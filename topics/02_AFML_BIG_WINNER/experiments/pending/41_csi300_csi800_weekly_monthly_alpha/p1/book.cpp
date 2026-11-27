// Sparse implementation of EP40's fixed-lot account. Each sleeve keeps its own cash
// and overdue lots. Opening orders cross within each sleeve before any cross-sleeve netting.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <map>
#include <vector>

struct Lot { double units; int due; };
extern "C" int replay(int n, int start, int end, int stop, int width,
    const int *target, const int *denom, const double *op, const double *cl,
    const unsigned char *buy, const unsigned char *sell, const int *actions, int na,
    int phase, int netting, double bf, double sf, double *out, const char *orderlog) {
    std::map<int,Lot> lots[10];
    double cash[10]={};
    for(int p=0;p<10;++p) cash[p]=phase<0 ? .1 : (p==phase);
    FILE *file=orderlog[0]?std::fopen(orderlog,"w"):nullptr;
    double lastnav=1;
    int until=stop+1;
    for(int i=start;i<=stop;++i) {
        int active=(i-start)%10;
        const double *price=op+size_t(i)*n, *mark=(i==end?op:cl)+size_t(i)*n;
        std::map<int,double> flow[10], wanted[10], blocked[10];
        std::map<int,double> buyers,sellers,positions;
        double planned=0,unfilled=0,openval=0;
        for(int p=0;p<10;++p) {
            if(phase>=0 && phase!=p)continue;
            const int *picks=target+size_t(i)*width;
            bool decision=(p==active && i+10<=end && denom[i]>0);
            bool expired=std::any_of(lots[p].begin(),lots[p].end(),[i](auto &h){return h.second.due<=i;});
            openval+=cash[p];
            for(auto &h:lots[p])openval+=h.second.units*price[h.first];
            if(!expired && !decision)continue;
            double locked=0,proceeds=0;
            for(auto it=lots[p].begin();it!=lots[p].end();) {
                int j=it->first; double amount=it->second.units*price[j];
                if(!std::isfinite(amount)){until=i;goto finish;}
                if(it->second.due<=i && sell[size_t(i)*n+j]){
                    proceeds+=amount;
                    int symbol=j;
                    for(int z=0;z<na;++z)
                        if(j==actions[3*z] && i>=actions[3*z+2])symbol=actions[3*z+1];
                    flow[p][symbol]-=amount;
                    it=lots[p].erase(it);
                } else {locked+=amount; if(it->second.due<=i)blocked[p][j]=amount; ++it;}
            }
            if(decision){
                int valid=0,count=0;
                for(;count<width && picks[count]>=0;++count){
                    int j=picks[count];
                    valid+=buy[size_t(i)*n+j] && !lots[p].count(j);
                }
                const double frac=double(valid)/denom[i], avail=cash[p]+proceeds*(1-sf);
                double allocation=std::min((avail+locked)/(1+bf*frac),
                        avail/(std::max(frac,1.e-12)*(1+bf)))/denom[i];
                planned+=allocation*count;
                unfilled+=allocation*(count-valid);
                for(int k=0;k<count;++k){
                    int j=picks[k]; wanted[p][j]=allocation;
                    if(!buy[size_t(i)*n+j] || lots[p].count(j) || allocation<=0)continue;
                    lots[p][j]={allocation/price[j],i+10};
                    flow[p][j]+=allocation;
                }
            }
            for(auto &f:flow[p]){
                if(f.second>0)buyers[f.first]+=f.second;
                else sellers[f.first]-=f.second;
            }
        }
        {
            double fees=0,cross=0,totalbuy=0,totalsell=0,nav=0,c=0;
            for(int p=0;p<10;++p) {
                for(auto &f:flow[p]){
                    int j=f.first;
                    double b=buyers[j],s=sellers[j],x=netting?std::min(b,s):0;
                    double left=f.second>0?f.second*(1-x/b):(s?f.second*(1-x/s):0);
                    double fee=left>0?bf*left:-sf*left;
                    cash[p]-=f.second+fee;fees+=fee;
                    if(left>0)totalbuy+=left;else totalsell-=left;
                    if(f.second>0)cross+=f.second-left;
                    if(file)std::fprintf(file,"%d,%d,%d,%.16g,%.16g,%.16g,%.16g,%.16g\n",i,p,j,wanted[p][j],f.second,left,fee,blocked[p][j]);
                }
                if(file){
                    for(auto &h:wanted[p])if(!flow[p].count(h.first))
                        std::fprintf(file,"%d,%d,%d,%.16g,0,0,0,%.16g\n",i,p,h.first,h.second,blocked[p][h.first]);
                    for(auto &h:blocked[p])if(!flow[p].count(h.first)&&!wanted[p].count(h.first))
                        std::fprintf(file,"%d,%d,%d,0,0,0,0,%.16g\n",i,p,h.first,h.second);
                }
                if(cash[p]<-1e-9){until=-1;goto finish;}
                c+=cash[p];
                for(auto &h:lots[p]){
                    double value=h.second.units*mark[h.first];
                    if(!std::isfinite(value)){until=i;goto finish;}
                    positions[h.first]+=value;nav+=value;
                }
            }
            nav+=c;
            double hhi=0,maxw=0;
            for(auto &v:positions){double w=v.second/nav; hhi+=w*w;maxw=std::max(maxw,w);}
            double vals[]={nav,c,fees,cross,totalbuy,totalsell,planned,unfilled,openval,nav-lastnav+fees,hhi,maxw,double(positions.size())};
            std::copy(vals,vals+13,out+size_t(i-start)*13);
            lastnav=nav;
        }
    }
finish:
    if(file)std::fclose(file);
    return until;
}
