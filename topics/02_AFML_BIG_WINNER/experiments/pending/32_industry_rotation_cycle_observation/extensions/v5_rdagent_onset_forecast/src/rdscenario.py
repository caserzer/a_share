"""EP32 custom scenario executed by the installed RD-Agent native five-step loop."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from rdagent.core.scenario import Scenario
from rdagent.core.proposal import Hypothesis, HypothesisGen, Hypothesis2Experiment, Experiment2Feedback, HypothesisFeedback
from rdagent.core.developer import Developer
from rdagent.core.experiment import Experiment, Task, FBWorkspace
from rdagent.oai.llm_utils import APIBackend
from common import OUT, CACHE, FEATURES, js, finite_json
from engine import validate_spec, search_evaluate, compile_features

STAGE=os.environ.get('EP32_STAGE','a')
DEST=OUT/f'stage_{STAGE}'


class IndustryScenario(Scenario):
    @property
    def background(self):
        target=('predict a future confirmed 6-18 calendar month industry upswing starting strictly within the next calendar month'
                if STAGE=='a' else 'recognize the first three calendar months of a future-confirmed 6-18 month industry upswing')
        return ('EP32: '+target+'. Industry return must be positive and exceed CSI300 or CSI_ALL. '
            'Causal features only; labels mature only at confirmed end, negatives require a later confirmed trough witness. '
            'All L2/L3 industries, separate SW2014 and SW2021 taxonomy eras. Historical-proxy, not certified PIT. '
            'Train labels available strictly before 2021-01-01. Feedback origins 2021-2022, labels mature before 2024. '
            'No access to later evaluation data. Weekly, biweekly, monthly share the same horizon/specification. '
            'Optimize equal-task Brier skill vs training prior; evaluate precision in top 10 percent and stability. '
            'Probability forecasts, rare events. Avoid class_weight=balanced because probabilities must remain meaningful.')
    @property
    def rich_style_description(self):return self.background
    def get_scenario_all_desc(self,*args,**kwargs):return self.background
    def get_runtime_environment(self):return 'Pinned local RD-Agent; deterministic restricted expression compiler; sklearn/LightGBM CPU'


def ask(prompt,tag):
    attempts=DEST/'llm';attempts.mkdir(parents=True,exist_ok=True)
    name=f'{tag}_{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")}'
    js(attempts/(name+'_request.json'),{'prompt':prompt,'no_outer_feedback':True})
    response=APIBackend().build_messages_and_create_chat_completion(user_prompt=prompt,
        system_prompt='You are a quantitative research agent. Return one JSON object only. Never use data not supplied.',
        json_mode=True,timeout=150)
    (attempts/(name+'_response.txt')).write_text(response)
    raw=response.strip()
    if raw.startswith('```'):raw=raw.split('\n',1)[1].rsplit('```',1)[0]
    return json.loads(raw)


class IndustryHypothesisGen(HypothesisGen):
    def gen(self,trace,plan=None):
        history=[]
        for exp,feedback in trace.hist:
            history.append(dict(id=getattr(exp,'candidate_id',None),spec=getattr(exp,'spec',None),
                result=getattr(exp,'result',None),feedback=str(feedback)))
        baseline=json.loads((DEST/'baseline_feedback.json').read_text())
        prompt=self.scen.background+'\nBase feature dictionary:\n'+json.dumps(FEATURES)+'''
momN is industry price change over N market sessions. ddN is current price / trailing N-session max - 1.
volN is trailing daily return standard deviation annualized. breadth21/63 is fraction of previous-month members
with positive stock returns. volume_ratio is mean current stock volume / its trailing63-session average.
coverage is current valid member endpoint fraction. log_members is log member count.
excessN is industry momN minus same-horizon benchmark return; marketN is benchmark return.
All are current/past-only features; missing historical values remain missing until train-only handling.
Return JSON with hypothesis (string), reason (string), spec (object).
spec keys ONLY: model, features, engineered, C, trees, leaves, max_depth, min_child_samples, learning_rate, reg_lambda.
model is logistic or lightgbm. features selects 2 to 31 base/engineered feature names, no duplicates.
engineered is a list of <=8 expression objects, each exactly {name,op,left,right}.
name must be a new valid Python identifier. op is add,sub,mul,div,abs,square.
left/right are an existing base/earlier engineered name or numeric constant in [-100,100].
div means left/(abs(right)+0.0001); abs/square ignore right but still require right:0.
No other operations, Python code, filenames, target variables, time identifiers, or industry identities.
C in [.001,10], trees integer[30,240], leaves integer[3,15], max_depth integer[2,5],
min_child_samples integer[50,1000], learning_rate[.01,.1], reg_lambda[0,100].
Use a small, scientifically motivated change. Generate a distinct specification.
No hyperparameter sweep. One specification is evaluated fairly on all 18 frequency/threshold/benchmark tasks.
'''+ '\nStatic baselines:\n'+json.dumps(baseline)+'\nPrior experiments:\n'+json.dumps(history[-8:])
        response=ask(prompt,f'round_{len(trace.hist):02d}')
        h=Hypothesis(hypothesis=response['hypothesis'],reason=response['reason'],concise_reason=response['reason'],
            concise_observation='Only 2021-2022 feedback',concise_justification='Prequential maturity controlled',
            concise_knowledge='No independent validation claim')
        h.spec=response['spec'];h.candidate_id=f'rd_{len(trace.hist):02d}'
        return h


class IndustryHypothesis2Experiment(Hypothesis2Experiment):
    def convert(self,hypothesis,trace):
        exp=Experiment([Task(hypothesis.candidate_id,description=hypothesis.hypothesis)],hypothesis=hypothesis)
        exp.spec=hypothesis.spec;exp.candidate_id=hypothesis.candidate_id
        exp.previous_specs=[getattr(e,'spec',{}) for e,_ in trace.hist]
        return exp


class IndustryCoder(Developer):
    def develop(self,exp):
        for attempt in range(3):
            try:
                validate_spec(exp.spec)
                assert exp.spec not in exp.previous_specs,'Duplicate previous specification'
                break
            except (AssertionError,KeyError,TypeError) as error:
                js(DEST/'repairs'/f'{exp.candidate_id}_{attempt}.json',{'spec':exp.spec,'error':str(error)})
                if attempt==2:raise
                exp.spec=ask('Repair this candidate specification. Return only {"spec": {...}}. '
                    'Use only these base fields '+json.dumps(FEATURES)+'. Keep schema from the original spec; '
                    'operators add/sub/mul/div/abs/square only; no labels/date fields. Error: '+str(error)+
                    '\nSpec:'+json.dumps(exp.spec),'repair_'+exp.candidate_id)['spec']
        ws=FBWorkspace(target_task=exp.sub_tasks[0])
        # Declarative program is the executable artifact. No untrusted arbitrary Python execution.
        ws.inject_files(**{'candidate.json':json.dumps(exp.spec,indent=2),
            'candidate.py':'# Validated feature program; evaluated only by the controlled engine.\nSPEC = '+repr(exp.spec)+'\n'})
        exp.sub_workspace_list=[ws]
        js(DEST/'candidates'/exp.candidate_id/'spec.json',exp.spec)
        return exp


class IndustryRunner(Developer):
    def develop(self,exp):
        exp.result=search_evaluate(exp.spec,STAGE,exp.candidate_id)
        print('EP32_ROUND_RESULT',exp.candidate_id,json.dumps(exp.result),flush=True)
        return exp


class IndustryFeedback(Experiment2Feedback):
    def generate_feedback(self,exp,trace):
        baseline=json.loads((DEST/'baseline_feedback.json').read_text())
        previous=[v['objective'] for v in baseline.values()]
        previous.extend(e.result['objective'] for e,_ in trace.hist if isinstance(getattr(e,'result',None),dict))
        best=max(previous);score=exp.result['objective'];decision=score>best
        feedback=HypothesisFeedback(reason=f'Equal-task Brier skill={score:.8f}; previous best={best:.8f}. '
            'Decision is search feedback only, not outer acceptance.',decision=decision,
            observations=json.dumps(exp.result),acceptable=decision)
        js(DEST/'candidates'/exp.candidate_id/'decision.json',{'decision':decision,'score':score,'previous_best':best})
        return feedback
