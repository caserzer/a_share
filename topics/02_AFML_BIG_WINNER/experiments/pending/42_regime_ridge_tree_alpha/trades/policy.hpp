// Close-time target selection hook for EP41's independently reconciled cash ledger.
#include <cstdint>
#include <functional>
#include <numeric>
#include <set>
#include <string>
struct Strategy {
    int n, days, mode, seats, width, bits, control, seed;
    const int *rank, *nvalid;
    const float *feat;
    const unsigned char *original;
    const int *ref;
    const double *refvalues;
    int *output;
    double *values;
};
static Strategy s;
extern "C" void configure(int n,int days,int mode,int seats,int width,int bits,int control,int seed,
    const int *rank,const int *nvalid,const float *features,const unsigned char *original,
    const int *ref,const double *refvalues,int *output,double *values) {
    s={n,days,mode,seats,width,bits,control,seed,rank,nvalid,features,original,ref,refvalues,output,values};
}
enum Field {TREE, SHALLOW, RISKCAP, RISKADV, ANNOUNCED, EXCESS, LEFT, RIGHT, LEFTQ, RIGHTQ, GATE,
            SECTOR, CAP, ADV, VOLQ, POS60, VOL60, MONEY};
enum Mode {HOLD, NATURAL, BUFFER, TAIL, SELL, MATCHED_CASH, OLD_BUFFER};
static int force_reference_state=0;
static double *inventory=nullptr;
extern "C" void capture_inventory(double *out){inventory=out;}
extern "C" void same_start_mode(int value){force_reference_state=value;}
static uint64_t hash64(uint64_t x){
    x+=0x9e3779b97f4a7c15ULL; x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;
    x=(x^(x>>27))*0x94d049bb133111ebULL; return x^(x>>31);
}
static void choose(int day,int k,const std::map<int,Lot> *lots,const double *cash,int ph,
                   const double *prev,const unsigned char *prev_sell,int *picks) {
    const int *rank=s.rank+size_t(day)*s.n;
    const unsigned char *prior=s.original+size_t(day)*s.n;
    int *log=s.output+size_t(day)*256;
    const int *ref=s.ref+size_t(day)*256;
    double *v=s.values+size_t(day)*10;
    const auto &held=lots[ph];
    auto f=[&](Field q,int j){return s.feat[(size_t(q)*s.days+day)*s.n+j];};
    auto randkey=[&](int j,int j2=0){return hash64((uint64_t(s.seed)*s.days+day)*s.n*s.n+uint64_t(j)*s.n+j2);};
    int n=s.nvalid[day], m=s.seats;
    std::vector<int> top(rank,rank+k), plan=top, remove,add, pool;
    std::set<int> chosen;
    double value=cash[ph];
    for(auto [j,lot]:held)value+=lot.units*prev[j];
    v[0]=value/k;
    if(inventory)for(auto [j,lot]:held)inventory[size_t(day)*s.n+j]=lot.units*prev[j];
    auto ticket_order=[&](const std::vector<int>& target) {
        std::map<int,double> flows;
        for (int j:target)flows[j]+=v[0];
        for(int p=0;p<10;++p)for (auto [j,lot]:lots[p])
            if(lot.due<=day && prev_sell[j])flows[j]-=lot.units*prev[j];
        double sum=0.;for(auto t:flows)sum+=std::abs(t.second);
        return sum;
    };
    auto sortby=[&](std::vector<int> &ids,auto score){std::stable_sort(ids.begin(),ids.end(),[&](int a,int b){
        auto x=score(a), y=score(b);
        if(x==y)return a<b;
        return x<y;
    });};
    for(int j:top)if(!held.count(j)&&!prior[j])++v[2];
    if(s.mode==HOLD){log[196]=held.size();int q=197;for(auto h:held)if(q<256)log[q++]=h.first;}
    else if(s.mode==NATURAL || s.mode==TAIL) {
        for(int j:top)if(!held.count(j)&&!prior[j])remove.push_back(j);
        int maxrank=s.width==3 ? k+3 : 2*k;
        for(int t=k;t<std::min(n,maxrank);++t){
            int j=rank[t];if(held.count(j)||prior[j])continue;
            if((s.bits&1)&&!(f(TREE,j)>.30f))continue;
            if((s.bits&2)&&f(RISKCAP,j)<=.10f&&f(RISKADV,j)<=.10f)continue;
            if((s.bits&4)&&f(ANNOUNCED,j)>.5)continue;
            pool.push_back(j);
        }
        if(s.mode==TAIL) {
            if(f(GATE,top[0])<.5)remove.clear();
            bool intersection=s.bits&32, upper=s.bits&16;
            remove.erase(std::remove_if(remove.begin(),remove.end(),[&](int j){
                if((intersection||upper)&&f(LEFTQ,j)<.85)return true;
                if(s.control!=0)return false;
                if(intersection)return f(RIGHTQ,j)>.5;
                return !(f(LEFT,j)>f(RIGHT,j));}),remove.end());
        }
        if(s.control==0){
            if(s.mode==TAIL)sortby(remove,[&](int j){return s.bits&32 ? -f(LEFT,j) : f(RIGHT,j)-f(LEFT,j);});
            else sortby(remove,[&](int j){return f((s.bits&8)?SHALLOW:TREE,j);});
        } else if(s.control==1){
            if(s.mode==TAIL)sortby(remove,[&](int j){return -f(LEFT,j);});
            else std::reverse(remove.begin(),remove.end());
        } else sortby(remove,[&](int j){return randkey(j);});
        if(s.control>0) {
            m=ref[0]; pool.clear();
            for(int t=0;t<ref[0];++t){int j=ref[65+t];if(!held.count(j)&&!prior[j])pool.push_back(j);}
        }
        m=std::min({m,int(remove.size()),int(pool.size())});
        remove.resize(m);add.assign(pool.begin(),pool.begin()+m);
    } else if(s.mode==OLD_BUFFER){
        plan.clear();
        const int *priorplan=day>=10?s.output+size_t(day-10)*256:nullptr;
        std::set<int> incumbents;
        if(priorplan && priorplan[129]>0)for(int h=0;h<priorplan[129];++h)incumbents.insert(priorplan[130+h]);
        for(int r=0;r<n/5 && int(plan.size())<k;++r)if(incumbents.count(rank[r]))plan.push_back(rank[r]);
        for(int r=0;r<n && int(plan.size())<k;++r)if(std::find(plan.begin(),plan.end(),rank[r])==plan.end())plan.push_back(rank[r]);
    } else if(s.mode==MATCHED_CASH){ plan.assign(top.begin(),top.begin()+ref[129]); } else if(s.mode==BUFFER){
        int entry=s.seats==24?24:k;
        std::vector<int> band,keep;
        for(int r=0;r<std::min(n,s.width);++r)if(held.count(rank[r])){
            keep.push_back(rank[r]);if(r>=entry)band.push_back(rank[r]);}
        if(s.bits&64){
            if(s.control==0) {
                for(int j:band)if(f(EXCESS,j)>.08)remove.push_back(j);
            } else {
                sortby(band,[&](int j){return randkey(j);});
                int cnt=std::min(int(band.size()),ref[0]);
                remove.assign(band.begin(),band.begin()+cnt);
            }
        }
        auto fill=[&](const std::vector<int>& released){
            std::set<int> dis(released.begin(),released.end());std::vector<int> v;
            for(int j:keep)if(!dis.count(j)&&int(v.size())<k)v.push_back(j);
            for(int t=0;t<entry&&int(v.size())<k;++t)
                if(std::find(v.begin(),v.end(),rank[t])==v.end())v.push_back(rank[t]);
            return v;
        };
        if(s.control==3&&!remove.empty()&&remove.size()<band.size()){
            // Random candidate sets, selected only using signal-close order estimates.
            double target=s.refvalues[day*10+1]/std::max(s.refvalues[day*10],1.e-15);
            auto err=[&](const std::vector<int>& z){return std::abs(ticket_order(fill(z))/std::max(v[0],1.e-15)-target);};
            double best=err(remove);
            for(int h=1;h<=12;++h){sortby(band,[&](int j){return randkey(j,h);});
                std::vector<int> z(band.begin(),band.begin()+remove.size());
                double val=err(z); if(val<best){best=val;remove=z;}}
        }
        plan=fill(remove);
    } else if(s.mode==SELL){
        m=k/5;add.assign(rank+k,rank+k+m);
        if(s.control<4){
            remove=top;
            if(s.control==0)sortby(remove,[&](int j){return f(TREE,j);});
            if(s.control==1)std::reverse(remove.begin(),remove.end());
            if(s.control==2)sortby(remove,[&](int j){return randkey(j);});
            if(s.control==3)sortby(remove,[&](int j){return s.bits==1 ? f(POS60,j) : s.bits==2 ? -f(VOL60,j) : f(MONEY,j);});
            remove.resize(m);
        }else{
            std::vector<int> old(top);
            sortby(old,[&](int j){return f(TREE,j);});old.resize(m);
            std::set<int> banned(old.begin(),old.end());std::vector<std::vector<int>> edges(m);
            for(int t=0;t<m;++t){
                int j=old[t];
                for(int h:top)if(!banned.count(h)&&f(SECTOR,j)>=0&&f(SECTOR,j)==f(SECTOR,h)){
                    bool match=s.control==4 ? std::abs(f(CAP,j)-f(CAP,h))<=.1 && std::abs(f(ADV,j)-f(ADV,h))<=.1 : std::abs(f(VOLQ,j)-f(VOLQ,h))<=.1;
                    if(match)edges[t].push_back(h);
                }
                sortby(edges[t],[&](int x){return randkey(x,j);});
            }
            std::map<int,int> owner;
            std::function<bool(int,std::set<int>&)> assign=[&](int a,std::set<int>& used){
                for(int j:edges[a])if(used.insert(j).second){
                    if(!owner.count(j)||assign(owner[j],used)){owner[j]=a;return true;}
                }return false;
            };
            std::vector<int> seq(m);std::iota(seq.begin(),seq.end(),0);
            sortby(seq,[&](int x){return randkey(old[x]);});
            for(int t:seq){std::set<int> used;assign(t,used);}
            remove=old;for(auto [newj,t]:owner)remove[t]=newj;v[3]=owner.size();
        }
    }
    if(s.mode!=BUFFER && s.mode!=MATCHED_CASH && s.mode!=OLD_BUFFER){
        chosen.insert(remove.begin(),remove.end()); plan.clear();
        for(int j:top)if(!chosen.count(j))plan.push_back(j);
        plan.insert(plan.end(),add.begin(),add.end());
    }
    if(s.mode==BUFFER)v[1]=ticket_order(plan);
    log[0]=remove.size();std::copy(remove.begin(),remove.end(),log+1);
    std::copy(add.begin(),add.end(),log+65);
    log[129]=plan.size();std::copy(plan.begin(),plan.end(),log+130);
    std::fill(picks,picks+64,-1);std::copy(plan.begin(),plan.end(),picks);
}
