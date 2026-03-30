# Related Work And Positioning

Purpose: position `KernelTuner` against the main adjacent research and tooling lines so the paper's literature review is coherent and scoped correctly.
Status: Backbone
Update Rule: update when the project's research posture changes materially or when a new prior-work bucket becomes central to the paper argument.
Feeds Paper Sections: Introduction, Related Work, Discussion, Limitations
Depends On: [01_research_program.md](01_research_program.md), [02_tuning_theory_and_knob_space.md](02_tuning_theory_and_knob_space.md), [04_signal_and_profiling_plan.md](04_signal_and_profiling_plan.md)

## Positioning Summary

`KernelTuner` sits in a deliberate middle ground:

- narrower than compiler-scale autoschedulers such as Halide and TVM-style systems,
- narrower than agentic or generative CUDA optimizers that synthesize or rewrite full kernels,
- but more structured and research-facing than simple benchmark-only tuning scripts.

The project does not ask the compiler to invent schedules from a rich transformation language. It also does not ask an agent to write new CUDA kernels from scratch. Instead, it fixes the Triton kernel implementation and studies whether a bottleneck-aware selector can spend a limited measurement budget better than defaults or naive search when choosing among bounded schedule configurations.

That is the right framing for the paper. The contribution is not "a new compiler" and not "a new kernel generator." The contribution is a reproducible systems study of lightweight Triton configuration selection, including both positive and bounded negative results.

## Main Related-Work Buckets

### 1. Algorithm-schedule separation and autoscheduling

The deepest conceptual ancestor is the Halide line of work. Halide made it natural to separate what a program computes from how it is scheduled, which in turn made automatic schedule search a well-posed optimization problem. Later Halide autoscheduling work showed that large schedule spaces can be explored automatically and even guided by learned methods.

Why this matters here:

- it legitimizes the schedule-first view taken by this project,
- it shows that schedule search is a real scientific problem rather than a bag of hand-tuned tricks,
- but it also highlights that `KernelTuner` is solving a much narrower problem than full autoscheduling.

Paper-facing distinction:

- Halide-style systems search over rich schedule languages with transformations over locality, recomputation, and parallel execution.
- `KernelTuner` searches over a compact Triton meta-parameter space with fixed kernel code.

### 2. Tensor-compiler autotuning and learned cost models

TVM, AutoTVM, Ansor, TensorIR, and MetaSchedule all study how to search large implementation spaces using a mix of sketches, learned cost models, and structured IR-level optimization.

Why this matters here:

- these systems are the closest scientific cousins in terms of "use evidence to search a performance space,"
- but they operate at a broader compiler/IR level than the bounded Triton tuning spaces in this repo,
- and they typically target much richer schedule spaces than the explicit knob families studied here.

Paper-facing distinction:

- those systems ask how to optimize tensor programs broadly;
- this project asks whether a much smaller, more practical Triton schedule space can be searched effectively with cheap signals and limited profiling under a matched budget.

### 3. Triton-native autotuning and heuristics

Triton already exposes the core ingredients of schedule tuning directly: tile sizes, warp counts, and pipeline stages. Its built-in facilities such as `triton.autotune` and `triton.heuristics` make benchmark-driven configuration search an expected workflow, especially for kernels like GEMM.

Why this matters here:

- it proves the problem is practically important inside the Triton ecosystem,
- it gives a strong default comparator,
- and it clarifies that the project is not trying to replace Triton itself.

Paper-facing distinction:

- Triton's native autotuning is still largely benchmark-first.
- `KernelTuner` studies whether candidate search can be made cheaper, more interpretable, and more reproducible by using compile-adjacent signals and limited profiling before brute-force benchmarking expands too far.

Important adjacent practical context:

- PyTorch's `torch.compile(mode="max-autotune")` explicitly exposes an autotuning-oriented mode and documents that it leverages Triton or template-based matrix multiplications on supported devices.
- That strengthens the practical motivation for this project: bounded tuning is not a niche curiosity, it is already part of the modern PyTorch/Triton stack.

### 4. External kernel autotuners

Frameworks such as Kernel Tuner, CLTune, and the Kernel Tuning Toolkit are particularly close in spirit. They treat kernels as parameterized programs, generate candidate settings, benchmark them, validate correctness, and compare search strategies.

Why this matters here:

- this is the clearest practical lineage for the repo architecture,
- it justifies treating kernel tuning as an external experimental framework rather than purely as a compiler pass,
- and it supports the emphasis on fair comparison, correctness validation, and structured artifacts.

Paper-facing distinction:

- `KernelTuner` is specialized to Triton and to a bottleneck-aware selector question rather than being a general-purpose autotuning shell.
- Its strongest differentiator is the explicit separation between reportable and diagnostic evidence, plus the use of the same artifact structure to explain both wins and failures.

### 5. Agentic and full-kernel GPU optimization

Recent work such as CUDA Agent and benchmarking efforts around agentic GPU optimization operate at a different level: generating or optimizing full CUDA kernels using broader search or learning loops.

Why this matters here:

- it is important modern context,
- it shows that GPU optimization is increasingly being treated as an automated search problem,
- but it also risks making this project look smaller or older-fashioned if the difference in scope is not stated clearly.

Paper-facing distinction:

- those systems optimize or synthesize whole kernels;
- this project keeps the Triton implementation fixed and asks a stricter question about budget-aware configuration selection.

That narrower scope is a strength, not a weakness: it makes negative results interpretable and allows matched-budget comparisons to remain fair.

### 6. Practical ecosystem evidence

The Triton and PyTorch ecosystem also provides a softer but important form of related work: tutorials, documentation, issue reports, and tools that exist because autotuning is still operationally messy in practice.

Why this matters here:

- official tutorials show that tuning is standard practice for Triton kernels,
- issue trackers show that autotuning can still be fragile around correctness, dynamic shapes, and codegen edge cases,
- and reuse-oriented tools such as `triton-dejavu` show that tuning overhead is itself a practical problem worth reducing.

This is not the paper's primary scientific basis, but it is valuable motivation. It helps explain why a lightweight, reproducible, budget-aware tuning study is still worth doing even in an ecosystem that already has built-in autotuning support.

### 7. Most recent adjacent direction: agentic kernel generation

The most recent online research pushes even farther than compiler autotuning by treating GPU optimization as an agentic synthesis problem. The clearest current example is CUDA Agent, which frames high-performance CUDA generation as a large-scale RL problem over full kernels rather than a bounded schedule-selection problem.

Why this matters here:

- it is the newest nearby line of research,
- it raises the bar for what "automatic GPU optimization" can mean in 2026,
- and it makes it even more important to explain why this project's narrower scope is still valuable.

Paper-facing distinction:

- CUDA Agent and similar systems optimize or generate full CUDA kernels.
- `KernelTuner` deliberately stays at the fixed-kernel Triton configuration layer, where matched-budget comparisons, bottleneck attribution, and bounded negative results remain much easier to interpret cleanly.

## What The Literature Implies For This Project

Taken together, the literature suggests three things:

1. Schedule search is a legitimate and important optimization problem.
2. Rich schedule spaces can produce large gains, but they also make causal interpretation and fair matched-budget comparison harder.
3. There is still room for narrower, more reproducible studies at the Triton configuration level, especially when the goal is to understand when cheap signals and limited profiling help and when they fail.

That is exactly the niche `KernelTuner` occupies.

## The Project's Distinctive Research Angle

The repo now supports a sharper literature-facing claim than it did at the start of the term.

The distinctive angle is not merely "Triton autotuning." It is:

- a fixed-kernel, schedule-first Triton tuning study,
- under explicit matched-budget rules,
- using a bottleneck-aware selector ladder,
- with clean separation between reportable and diagnostic profiling,
- and with enough artifact structure to support failure analysis and keep/drop decisions.

This matters because much of the surrounding literature emphasizes either:

- broader search power,
- broader compiler control,
- or end-to-end optimization wins.

`KernelTuner` instead emphasizes:

- credibility,
- scope discipline,
- and explanation quality.

## How This Should Shape The Paper Narrative

The literature review should make four moves in order:

1. Start from schedule search as a general idea.
   Use Halide and TVM-style systems to establish that schedule choice strongly affects performance and that automated search is a serious research topic.

2. Narrow to Triton.
   Explain that Triton exposes a smaller but still meaningful schedule/configuration space where practitioners routinely tune tile sizes, warps, and stages.

3. Position against practical autotuners.
   Show that external kernel autotuners already justify the "parameterized kernel + search + validation + benchmarking" framing.

4. Clarify the paper's niche.
   State that this project studies whether lightweight compile-adjacent signals and limited profiling can guide Triton configuration search under a fair, matched budget, and that the scientific value includes principled negative results as well as wins.

## Literature-Driven Scope Discipline

The literature also justifies some of the repo's final keep/drop decisions.

- The project does not need to grow into a full compiler autoscheduler to be publishable; that would move it into a different research category.
- It does not need to beat agentic CUDA systems at full-kernel generation; that is a different problem.
- It does need to show that its narrower scope is meaningful, methodologically clean, and honest about transfer failures.

That is why the final paper should keep:

- representative GEMM as the truth source,
- aligned GEMM as supporting context,
- LayerNorm as a bounded regime-split secondary story,
- and the Phase 3 transfer result as a useful limit case rather than a reason to reopen the whole search space.

## Writing Guidance

When the paper is drafted, this document should drive the Related Work section.

Allowed emphasis:

- schedule-first tuning as a middle-ground research problem,
- Triton as a practical but still under-structured tuning environment,
- matched-budget evidence and artifact quality as key methodological strengths,
- and bounded negative results as part of the contribution.

Avoid:

- claiming novelty for schedule search itself,
- implying the project is a general Triton autoscheduler,
- or positioning the work as a replacement for compiler-scale autotuning or full-kernel agentic optimization.

## Reference Shelf

Core sources that should anchor the paper's Related Work section:

- [Ragan-Kelley et al., "Decoupling Algorithms from Schedules for Easy Optimization of Image Processing Pipelines" (SIGGRAPH 2012)](https://people.csail.mit.edu/jrk/halide12/)
- [Mullapudi et al., "Automatically Scheduling Halide Image Processing Pipelines" (SIGGRAPH 2016)](https://graphics.cs.cmu.edu/projects/halidesched/)
- [Adams et al., "Learning to Optimize Halide with Tree Search and Random Programs" (SIGGRAPH 2019)](https://halide-lang.org/papers/halide_autoscheduler_2019.pdf)
- [Chen et al., "Learning to Optimize Tensor Programs" (NeurIPS 2018 / AutoTVM)](https://papers.nips.cc/paper/7599-learning-to-optimize-tensor-programs)
- [Zheng et al., "TensorIR: An Abstraction for Automatic Tensorized Program Optimization" (2022)](https://arxiv.org/abs/2207.04296)
- [MetaSchedule / "Tensor Program Optimization with Probabilistic Programs" (2022)](https://arxiv.org/abs/2205.13603)
- [Tillet, Kung, and Cox, "Triton: An intermediate language and compiler for tiled neural network computations" (MAPL 2019)](https://research.ibm.com/publications/triton-an-intermediate-language-and-compiler-for-tiled-neural-network-computations)
- [OpenAI, "Introducing Triton" (2021)](https://openai.com/index/triton/)
- [Triton `triton.autotune` documentation](https://triton-lang.org/main/python-api/generated/triton.autotune.html)
- [Triton `triton.heuristics` documentation](https://triton-lang.org/main/python-api/generated/triton.heuristics.html)
- [van Werkhoven, "Kernel Tuner: A search-optimizing GPU code auto-tuner" (2019)](https://www.sciencedirect.com/science/article/pii/S0167739X18313359)
- [Nugteren and Corporaal, "CLTune: A Generic Auto-Tuner for OpenCL Kernels" (2015)](https://cnugteren.github.io/downloads/Nugteren2015a.pdf)
- [Petrov et al., "Kernel Tuning Toolkit" (SoftwareX 2023)](https://www.sciencedirect.com/science/article/pii/S235271102300081X)
- [IBM `triton-dejavu` repository](https://github.com/IBM/triton-dejavu)
- [PyTorch `torch.compile` documentation](https://docs.pytorch.org/docs/stable/generated/torch.compile.html)
- [PyTorch tutorial on user-defined Triton kernels with `torch.compile`](https://docs.pytorch.org/tutorials/recipes/torch_compile_user_defined_triton_kernel_tutorial.html)
- [Dai et al., "CUDA Agent: Large-Scale Agentic RL for High-Performance CUDA Kernel Generation" (2026)](https://arxiv.org/abs/2602.24286)
