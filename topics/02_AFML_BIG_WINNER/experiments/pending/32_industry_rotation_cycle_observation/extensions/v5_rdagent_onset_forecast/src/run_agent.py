"""Run 30 native RDLoop cycles with isolated traces and frozen evaluator."""
import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from dotenv import dotenv_values
from common import ROOT, OUT, CACHE, RD, js, sha


def main():
    stage='b' if '--stage-b' in sys.argv else 'a'
    env=dotenv_values(RD/'.env')
    for key in ['OPENROUTER_API_KEY','OPENAI_API_KEY']:
        if env.get(key):os.environ[key]=env[key]
    # Respect the active session transport; an older RD-Agent .env proxy is stale.
    for upper in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY']:
        value=os.environ.get(upper) or os.environ.get(upper.lower()) or env.get(upper)
        if value:
            os.environ[upper]=value;os.environ[upper.lower()]=value
    model=env.get('CHAT_MODEL','')
    assert model and os.environ.get('OPENROUTER_API_KEY')
    if not model.startswith('openrouter/'):model='openrouter/'+model
    attempt=1
    while (CACHE/f'stage_{stage}/rdagent_trace_{attempt:02d}').exists():attempt+=1
    trace=CACHE/f'stage_{stage}/rdagent_trace_{attempt:02d}'
    os.environ.update(EP32_STAGE=stage,LOG_TRACE_PATH=str(trace),WORKSPACE_PATH=str(CACHE/f'stage_{stage}/workspaces'),
        PICKLE_CACHE_FOLDER_PATH_STR=str(CACHE/f'stage_{stage}/pickle_cache'),
        PROMPT_CACHE_PATH=str(CACHE/f'stage_{stage}/prompt_cache.db'),
        CHAT_MODEL=model,LITELLM_CHAT_MODEL=model,CHAT_STREAM='false',LITELLM_CHAT_STREAM='false',
        LOG_LLM_CHAT_CONTENT='false',LITELLM_LOG_LLM_CHAT_CONTENT='false',
        CHAT_MAX_TOKENS='4096',LITELLM_CHAT_MAX_TOKENS='4096',MAX_RETRY='2',LITELLM_MAX_RETRY='2',
        ENABLE_RESPONSE_SCHEMA='false',LITELLM_ENABLE_RESPONSE_SCHEMA='false',
        BACKEND='rdagent.oai.backend.LiteLLMAPIBackend',STEP_SEMAPHORE='1',MULTI_PROC_N='1')
    # Trace only contains sanitized configuration. API keys remain in environment/private runtime.
    commit=subprocess.check_output(['git','-C',str(RD),'rev-parse','HEAD'],text=True).strip()
    diff=subprocess.check_output(['git','-C',str(RD),'diff','--binary'])
    import hashlib
    runtime=dict(rdagent_commit=commit,adapter_diff_sha256=hashlib.sha256(diff).hexdigest(),model=model,
        loop_budget=30,trace=str(trace),scenario='rdscenario.IndustryScenario',quality='Historical-proxy',
        research_plan_sha256=sha(ROOT/'research_plan.md'),
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src').glob('*.py'))})
    if (OUT/f'stage_{stage}/runtime.json').exists():
        previous=json.loads((OUT/f'stage_{stage}/runtime.json').read_text())
        js(OUT/f'stage_{stage}/runtime_previous_{attempt:02d}.json',previous)
    js(OUT/f'stage_{stage}/runtime.json',runtime)
    sys.path.insert(0,str(RD))
    from rdagent.components.workflow.conf import BasePropSetting
    from rdagent.components.workflow.rd_loop import RDLoop
    settings=BasePropSetting(scen='rdscenario.IndustryScenario',hypothesis_gen='rdscenario.IndustryHypothesisGen',
        hypothesis2experiment='rdscenario.IndustryHypothesis2Experiment',coder='rdscenario.IndustryCoder',
        runner='rdscenario.IndustryRunner',summarizer='rdscenario.IndustryFeedback')
    loop=RDLoop(settings)
    asyncio.run(loop.run(loop_n=30,all_duration='4h'))
    sessions=[]
    for p in sorted((trace/'__session__').glob('*')):
        sessions.append(dict(loop=p.name,checkpoints=sorted(f.name for f in p.iterdir() if f.is_file())))
    js(OUT/f'stage_{stage}/run_complete.json',{'completed_history':len(loop.trace.hist),'sessions':sessions,
        'native_steps':loop.steps,'requested_rounds':30})
    assert len(loop.trace.hist)==30, '30 rounds not complete; inspect preserved runtime evidence'
    print('EP32_RDAGENT_COMPLETE',stage,len(loop.trace.hist),flush=True)


if __name__=='__main__':main()
