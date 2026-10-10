# Survey on LLM Agents and Tool Use

## TL;DR
- LLM agents leverage modular architectures that enhance performance through reasoning, planning, and memory integration [1].
- The integration of supervised fine-tuning with reinforcement learning optimizes training outcomes, demonstrating over three points improvement in benchmark tasks [2].
- Benchmarking frameworks such as AGENTBENCH and AGENCYBENCH reveal significant performance differences in LLMs across real-world applications [3][4].
- Multi-agent systems are evolving as a trend, emphasizing collaborative capabilities and the establishment of systematic evaluation methodologies in real-world applications [5].

## Background
Large Language Models (LLMs) are increasingly being deployed as autonomous agents capable of performing complex tasks using natural language processing. Historically, LLMs have been predominantly used for text generation, but recent advancements have shifted focus towards their application as agents that can reason, plan, and utilize tools to execute tasks robustly. Foundational papers emphasize the need for modular architectures that integrate various functionalities necessary for autonomous operation [1].

## Core Architectures
The exploration of core architectures reveals that LLM agents optimize their task execution through varying frameworks combining memory, reasoning, and planning. For instance, the integration of Chain-of-Thought and Tree-of-Thought architectures has shown promise in enhancing problem-solving capabilities [1]. Furthermore, frameworks like Agent LUMOS highlight the benefits of a modular training architecture that supports scalability and flexibility across different tasks [6]. Notably, systems such as AgentDock underline the importance of component separation for task orchestration and tool utilization [7].

## Training and Optimization Paradigms
Recent paradigms in training LLM agents emphasize hybrid approaches that mesh supervised learning with reinforcement learning methods. The BRIDGE framework exemplifies this by demonstrating improved reasoning capabilities based on integrated training strategies [2]. Furthermore, Staged RL Training prioritizes action generation to refine reasoning processes effectively, signifying an innovative approach to enhancing performance in complex environments [8]. These methods significantly reduce the manual effort required in constructing optimization pipelines and highlight a shift towards automated frameworks [9].

## Empirical Benchmarks and Applications
Empirical evaluations through frameworks such as SciAssess and VitaBench emphasize the significance of real-world task applicability and interaction capabilities of LLM agents [10][11]. Benchmarking tools also indicate that smaller, domain-specialized models can outperform larger universal models, particularly in threat detection and task execution [12]. The disparities in agent performance showcased by AGENCYBENCH reveal the ongoing challenges in agent robustness and adaptability across varied contexts [4].

## Emerging Trends
The future of LLM agents points towards multi-agent systems that can facilitate collaboration in problem-solving tasks. Recent literature stresses the importance of evolving evaluation methodologies to assess agent performance comprehensively across diverse operational environments [5][13]. This trend signifies a paradigm shift towards developing agent systems capable of handling more complex, interactive tasks in dynamic settings [14][15]. Furthermore, frameworks like FutureX aim to enhance predictive capabilities, thereby expanding the functional repertoire of LLM agents in practical applications [16].

## Trends and Open Problems
In the last two years, there has been a noticeable shift in the focus of LLM agents from mere task execution to an emphasis on safety, reliability, and collaboration. Ongoing challenges include ensuring the adaptability of these agents in real-world contexts and developing systematic, standardized evaluation metrics [5]. Addressing these issues will be critical in advancing LLM technologies toward their full potential in practical applications.

## References
[1] Fundamentals of Building Autonomous LLM Agents. arxiv. https://arxiv.org/html/2510.09244v1 (N/A)
[2] BRIDGE: A Scalable Framework for Integrating Supervised Fine-Tuning and Reinforcement Learning. web. https://arxiv.org/pdf/2509.06948 (N/A)
[3] AGENTBENCH. web. https://proceedings.iclr.cc/paper_files/paper/2024/file/e9df36b21ff4ee211a8b71ee8b7e9f57-Paper-Conference.pdf (2024)
[4] AGENCYBENCH: Benchmarking the Frontiers of Autonomous Agents in 1M-Token Real-World Contexts. web. https://aclanthology.org/2026.acl-long.337.pdf (2026)
[5] From Language Models to Agentic AI: A Survey of Autonomous, Action-Enabled, and Collaborative LLM Agents. web. https://link.springer.com/article/10.1007/s12559-026-10619-1 (2026-08-24)
[6] Agent LUMOS: Unified and Modular Training for Open-Source Language Agents. web. https://aclanthology.org/2024.acl-long.670.pdf (N/A)
[7] Core Architecture Overview - AgentDock Documentation. web. https://hub.agentdock.ai/docs/architecture/core/overview (N/A)
[8] Staged RL Training for LLM Agents. web. https://ojs.aaai.org/index.php/AAAI/article/view/40794/44755 (N/A)
[9] LaMDAgent: An Autonomous Framework for Post-Training Pipeline Optimization via LLM Agents. hf-search. https://huggingface.co/papers/2505.21963 (2025-05-28)
[10] SciAssess: Benchmarking LLM Proficiency in Scientific Literature Analysis. hf-search. https://huggingface.co/papers/2403.01976 (2024-03-04)
[11] VitaBench: Benchmarking LLM Agents with Versatile Interactive Tasks in Real-world Applications. hf-search. https://huggingface.co/papers/2509.26490 (2025-09-30)
[12] MolErr2Fix: Benchmarking LLM Trustworthiness in Chemistry via Modular Error Detection, Localization, Explanation, and Revision. hf-search. https://huggingface.co/papers/2509.00063 (2025-08-26)
[13] LLM-based agent systems: a systematic literature review and position on hybrid architectures and evaluation frameworks. web. https://dl.acm.org/doi/10.1007/s10489-026-07340-9 (2026-07-01)
[14] Survey on Evaluation of LLM-based Agents. hf-search. https://huggingface.co/papers/2503.16416 (2025-03-20)
[15] LangChain State of AI Agents Report: 2024 Trends. web. https://www.langchain.com/stateofaiagents (2026-06-12)
[16] FutureX: An Advanced Live Benchmark for LLM Agents in Future Prediction. hf-search. https://huggingface.co/papers/2508.11987 (2025-08-16)
