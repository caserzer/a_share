// Historical EP40 ten-sleeve account. Orders net first within each sleeve and
// then across sleeves. Report quantities in units of initial account equity.
#include <algorithm>
#include <array>
#include <cmath>
#include <vector>

struct Lot {int stock, due; double units;};
struct Order {int phase, stock; double value;};
extern "C" int replay(
    int n, int width, int first, int stop, int horizon_end, int predecessor,
    int successor, int listing, int predecessor2, int successor2, int listing2, const double *op, const double *cl,
    const unsigned char *canbuy, const unsigned char *cansell,
    const int *targets, double fee_mult, double *daily, double *trades,
    int *missing) {
    std::array<std::vector<Lot>,10> lots;
    std::array<double,10> cash; cash.fill(.1);
    std::vector<double> buy(n),sell(n),flow(n);
    std::vector<int> changed, touched; std::vector<Order> orders;
    std::vector<unsigned char> used(n), changed_flag(n);
    double prev = 1;
    for(int i=first;i<=stop;i++) {
        auto p = op+size_t(i)*n;
        auto m = i==horizon_end ? p : cl+size_t(i)*n;
        touched.clear(); orders.clear();
        double blocked=0, attempted=0, blocked_sells=0;
        for(int h=0;h<10;h++) {
            bool scheduled=(i-first)%10==h;
            auto &book=lots[h];
            bool processing=scheduled || std::any_of(book.begin(),book.end(),[&](Lot l){return l.due<=i;});
            if(!processing)continue;
            changed.clear();
            auto add=[&](int s,double x) {
                if(!changed_flag[s]) { changed.push_back(s);changed_flag[s]=true; }
                flow[s]+=x;
            };
            double sales=0, locked=0;
            std::vector<Lot> retained;
            for(auto l:book) {
                int s=l.stock;
                if(!std::isfinite(p[s])) {missing[0]=s;missing[1]=0;return i;}
                double v=l.units*p[s];
                if(l.due<=i && cansell[size_t(i)*n+s]){
                    sales+=v; add(s==predecessor && i>=listing?successor:(s==predecessor2 && i>=listing2 ? successor2:s),-v);
                } else {
                    if(l.due<=i) blocked_sells+=v;
                    locked+=v; retained.push_back(l);
                }
            }
            book.swap(retained);
            if(scheduled && i+10<=horizon_end) {
                int count=0;std::vector<int> allowed;
                auto pick=targets+size_t(i)*width;
                for(; count<width && pick[count]!=-1;count++) {
                    int s=pick[count];
                    if(s<0 || !canbuy[size_t(i)*n+s])continue;
                    if(std::none_of(book.begin(),book.end(),[&](Lot l){return l.stock==s;}))
                        allowed.push_back(s);
                }
                if(count) {
                    double fraction=double(allowed.size())/count;
                    double avail=cash[h]+sales*(1-.002*fee_mult);
                    double scale=std::min((avail+locked)/(1+.001*fee_mult*fraction),
                                      avail/(std::max(1e-12,fraction)*(1+.001*fee_mult)));
                    attempted+=scale;
                    blocked+=scale*(1.-fraction);
                    for(int s:allowed) {
                        double amount=scale/count;
                        if(amount>0) {book.push_back({s,i+10,amount/p[s]});add(s,amount);}
                    }
                }
            }
            for(int s:changed) {
                double v=flow[s];flow[s]=0;changed_flag[s]=false;
                if(v==0)continue;
                if(!used[s]) {used[s]=true;touched.push_back(s);}
                orders.push_back({h,s,v});cash[h]-=v;
                if(v>0)buy[s]+=v;else sell[s]-=v;
            }
        }
        double paid=0,cross=0,total_buy=0,total_sell=0;
        for(auto order:orders) {
            int s=order.stock;double overlap=std::min(buy[s],sell[s]),v=order.value;
            double fee=(v>0?.001*v*(1-overlap/buy[s]):-.002*v*(1-overlap/sell[s]))*fee_mult;
            cash[order.phase]-=fee;paid+=fee;
        }
        for(int s:touched) {
            double net=buy[s]-sell[s];cross+=std::min(buy[s],sell[s]);
            if(net>0)total_buy+=net;else total_sell-=net;
            if(trades)trades[size_t(i-first)*n+s]=net;
            buy[s]=sell[s]=0;used[s]=false;
        }
        double funds=0,nav=0;
        for(int h=0;h<10;h++) {
            if(cash[h]<-1e-9)return -2;
            funds+=cash[h];
            for(auto l:lots[h]) {
                if(!std::isfinite(m[l.stock])) {missing[0]=l.stock;missing[1]=1;return i;}
                nav+=l.units*m[l.stock];
            }
        }
        nav+=funds;
        double *row=daily+(i-first)*10;
        double values[]={nav,funds,paid,cross,total_buy,total_sell,attempted,blocked,blocked_sells,prev};
        std::copy(values,values+10,row);prev=nav;
    }
    return -1;
}
