#include <numeric>
#include <fstream>
struct Settings { int mode; double cap,tau; } conf{};
extern "C" void setup43(int mode,double cap,double tau){conf={mode,cap,tau};}
static FILE* audit43=nullptr;
static int audit_day=0;
static double last_L1_43=0;
static bool measure_L1_43=false;
extern "C" void audit43_open(const char* name){
    if(audit43){std::fclose(audit43);audit43=nullptr;}
    if(name && name[0])audit43=std::fopen(name,"w");
}
struct Piece {double slope, amount;int j,first;};
void choose43(int width,int k,const int* picks,const double* rank,const std::map<int,Lot>& held,
              double cash,const double* close,const unsigned char* sell,
              std::vector<int>& ids,std::vector<double>& weight){
    int n=0;
    while(n<width && picks[n]>=0)++n;
    if(conf.mode<=2){
        int bound=conf.mode==1?int(std::ceil(1.35*k)):40;
        for(int j=0;j<std::min(n,bound) && (int)ids.size()<k;++j)
            if(held.count(picks[j]))ids.push_back(picks[j]);
        for(int j=0;j<n && (int)ids.size()<k;++j)
            if(std::find(ids.begin(),ids.end(),picks[j])==ids.end())ids.push_back(picks[j]);
        weight.assign(ids.size(),1./k);return;
    }
    double wealth=cash;
    for(auto &h:held)wealth+=h.second.units*close[h.first];
    double free=1.,cap=conf.cap>0?conf.cap:1./k;
    std::vector<double> old(n),upper(n,cap),lp(n),zero(n),out(n);
    for(auto &h:held)if(!sell[h.first]){
        double w=h.second.units*close[h.first]/wealth;
        ids.push_back(h.first);weight.push_back(w);free-=w;
    }
    for(int j=0;j<n;++j){
        auto it=held.find(picks[j]);
        if(it!=held.end()){
            if(!sell[picks[j]])upper[j]=0;
            else old[j]=it->second.units*close[picks[j]]/wealth;
        }
    }
    double budget=std::max(0.,std::min(free,std::accumulate(upper.begin(),upper.end(),0.)));
    auto linear=[&](double tau,std::vector<double>& w){
        std::vector<Piece> pieces;
        for(int j=0;j<n;++j){
            double mid=std::min(old[j],upper[j]);
            if(mid>0)pieces.push_back({rank[j]+tau,mid,j,1});
            if(upper[j]>mid)pieces.push_back({rank[j]-tau,upper[j]-mid,j,0});
        }
        std::sort(pieces.begin(),pieces.end(),[&](auto a,auto b){
            if(a.slope!=b.slope)return a.slope>b.slope;
            if(a.first!=b.first)return a.first>b.first;
            return picks[a.j]>picks[b.j];});
        double rem=budget;
        for(auto &s:pieces){double take=std::min(rem,s.amount);w[s.j]+=take;rem-=take;if(rem<=0)break;}
    };
    linear(conf.tau,lp);out=lp;
    if(conf.mode==4){
        auto alloc=[&](int j,double mu){
            double d=rank[j]-mu;
            double step=std::copysign(std::max(0.,std::abs(d)-conf.tau),d)/k;
            return std::clamp(old[j]+step,0.,upper[j]);};
        double lo=-2.-k,hi=2.+k;
        for(int it=0;it<64;++it){
            double mid=(lo+hi)/2,sum=0;
            for(int j=0;j<n;++j)sum+=alloc(j,mid);
            if(sum>budget)lo=mid;else hi=mid;
        }
        for(int j=0;j<n;++j)out[j]=alloc(j,(lo+hi)/2);
    }
    if(conf.mode==5){
        linear(0,zero);
        // Mandatory cap clipping occurs first; reference and LP have identical forced exits.
        double a=0,b=0;
        for(int j=0;j<n;++j){old[j]=std::min(old[j],upper[j]);a+=std::abs(lp[j]-old[j]);b+=std::abs(zero[j]-old[j]);}
        double alpha=b>0?std::min(1.,a/b):1;
        for(int j=0;j<n;++j)out[j]=old[j]+alpha*(zero[j]-old[j]);
    }
    double residual=std::abs(budget-std::accumulate(out.begin(),out.end(),0.));
    if(audit43){
        double up=-1e99,down=1e99,bound=0,delta=0,ticket=0,hhi=0,top=0;
        for(int j=0;j<n;++j){
            double w=out[j],d=w-old[j],s=rank[j]-(conf.mode==4?k*d:0.);
            if(w<upper[j]-1e-10)up=std::max(up,s+(d< -1e-10?conf.tau:-conf.tau));
            if(w>1e-10)down=std::min(down,s+(d>1e-10?-conf.tau:conf.tau));
            bound=std::max(bound,std::max(-w,w-upper[j]));delta+=std::abs(d);ticket+=w;hhi+=w*w;
            if(j<10)top+=w;
        }
        std::fprintf(audit43,"%d,%.15g,%.15g,%.15g,%.15g,%.15g,%.15g,%.15g,%.15g,%zu\n",
                     audit_day,wealth,residual,bound,std::max(0.,up-down),delta,ticket,hhi,top,ids.size());
    }
    if(conf.mode!=5 && residual>1e-8)throw std::runtime_error("budget residual");
    for(int j=0;j<n;++j)if(out[j]>1e-14){ids.push_back(picks[j]);weight.push_back(out[j]);}
    if(measure_L1_43){
        std::map<int,double> gaps;
        for(auto &h:held)gaps[h.first]-=h.second.units*close[h.first]/wealth;
        for(size_t j=0;j<ids.size();++j)gaps[ids[j]]+=weight[j];
        last_L1_43=0.;for(auto &v:gaps)last_L1_43+=std::abs(v.second);
    }
}
