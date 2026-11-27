#include <array>
struct Snapshot {std::array<std::map<int,Lot>,10> lots;std::array<double,10> cash;};
static std::map<int,Snapshot> snapshots;
static int record43=0,base43=-1,fork43=-1,alternate43=3;
static double wealth43=0,start43=0;
extern "C" void fork_config(int record,int base,int fork,int alternative){
    record43=record;base43=base;fork43=fork;alternate43=alternative;
    if(record)snapshots.clear();
}
extern "C" double fork_nav(){return wealth43;}

extern "C" double fork_start(){return start43;}

static FILE* goals43=nullptr;
extern "C" void goal_log(const char* name){
    if(goals43){std::fclose(goals43);goals43=nullptr;}
    if(name && name[0])goals43=std::fopen(name,"wb");
}

extern "C" double fork_l1(){return last_L1_43;}
