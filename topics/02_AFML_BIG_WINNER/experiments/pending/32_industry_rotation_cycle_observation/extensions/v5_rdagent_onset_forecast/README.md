# EP32 V5

[完整报告](reports/rdagent_observation.md)；[冻结方案](research_plan.md)。

项目虚拟环境运行data.py、labels.py；RD-Agent虚拟环境运行engine.py、run_agent.py、outer.py。阶段A全部未通过后，依次early_labels.py、engine.py --stage-b、run_agent.py --stage-b、outer.py --stage-b。最后运行report.py与validate.py。大型面板、原生trace和完整预测在私有缓存中。
