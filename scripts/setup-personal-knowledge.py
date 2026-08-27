# -*- coding: utf-8 -*-
"""一次性：汇总 Obsidian + gds-ai-experience + 旧 knowledge 到 personal-knowledge。"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\tl_94\PycharmProjects\personal-knowledge")
OLD = Path(r"C:\Users\tl_94\PycharmProjects\personal-hr-agent\knowledge")
OBS = Path(r"D:\obsidian\repo\知识库")
GDS = Path(r"C:\Users\tl_94\PycharmProjects\myAIProjects\gds-ai-experience\docs")
RESUMES = Path(r"C:\Users\tl_94\PycharmProjects\myAIProjects\docs")

DIRS = [
    "_meta",
    "01-基本信息",
    "02-工作经历",
    "03-项目经历-在职",
    "04-项目经历-架构理解",
    "05-技能与问答",
    "06-原始资料-gds",
    "07-原始资料-obsidian",
    "08-简历参考",
]

# (src relative to base, dst relative to ROOT)
OLD_MAP = {
    "basics/identity.md": "01-基本信息/identity.md",
    "basics/education.md": "01-基本信息/education.md",
    "basics/job-search.md": "01-基本信息/job-search.md",
    "basics/leaving-narrative.md": "01-基本信息/leaving-narrative.md",
    "basics/availability.md": "01-基本信息/availability.md",
    "basics/compensation.md": "01-基本信息/compensation.md",
    "career/timeline.md": "02-工作经历/timeline.md",
    "career/01-zhongyi-suzhou.md": "02-工作经历/01-zhongyi-suzhou.md",
    "career/02-huibo-ericsson.md": "02-工作经历/02-huibo-ericsson.md",
    "career/03-huaqin-ebay.md": "02-工作经历/03-huaqin-ebay.md",
    "profile.md": "01-基本信息/profile-summary.md",
    "resume.md": "02-工作经历/resume-summary.md",
    "skills.md": "05-技能与问答/skills.md",
    "stories.md": "05-技能与问答/stories.md",
    "faq.md": "05-技能与问答/faq.md",
    "boundaries.md": "05-技能与问答/boundaries.md",
    "projects/knowledge-rag-platform.md": "04-项目经历-架构理解/knowledge-rag-platform.md",
    "projects/governance-agent.md": "04-项目经历-架构理解/governance-agent.md",
    "projects/ops-oncall-agent.md": "04-项目经历-架构理解/ops-oncall-agent.md",
    "projects/personal-hr-agent.md": "04-项目经历-架构理解/personal-hr-agent.md",
}

OBS_MAP = {
    r"面试\田麟 - 后端开发工程师.md": "07-原始资料-obsidian/田麟-后端开发工程师-主简历.md",
    r"GDS_AI_Agent_简历项目经历_整合版.md": "07-原始资料-obsidian/GDS-AI-Agent-简历整合版.md",
    r"GDS_Platform_Resume.md": "07-原始资料-obsidian/GDS-Platform-Resume.md",
    r"CJS_Platform_Resume.md": "07-原始资料-obsidian/CJS-Platform-Resume.md",
    r"Technical_Architecture.md": "07-原始资料-obsidian/GDS-Technical-Architecture.md",
    r"Branch_Function_Detail.md": "07-原始资料-obsidian/GDS-Branch-Function-Detail.md",
    r"Agent_Analysis\01_HubGptAgent_告警分析.md": "07-原始资料-obsidian/Agent-HubGpt.md",
    r"Agent_Analysis\02_ContractAgent_表上线.md": "07-原始资料-obsidian/Agent-Contract.md",
    r"Agent_Analysis\03_SqlLineageAgent_血缘分析.md": "07-原始资料-obsidian/Agent-SqlLineage.md",
    r"Agent_Analysis\04_Agent接口与AbstractChatAgent_抽象基类.md": "07-原始资料-obsidian/Agent-AbstractChatAgent.md",
    r"大营销\面试项目总结-BigMarket.md": "07-原始资料-obsidian/BigMarket-面试总结.md",
    r"大营销\压测环境配置.md": "07-原始资料-obsidian/BigMarket-压测环境配置.md",
    r"大营销\真实架构说明.md": "07-原始资料-obsidian/BigMarket-真实架构说明.md",
}

GDS_FILES = [
    "最有价值文档清单.md",
    "overview/README.md",
    "overview/00_三项目容量总览.md",
    "overview/rag/RAG_主流程梳理.md",
    "architectures/治理数据Agent项目_整体架构与功能说明.md",
    "architectures/运维OncallAgent项目_整体架构与功能说明.md",
    "articles/rag/Hybrid_Retrieval_设计与实现.md",
    "functions/Knowledge_Base_Ingestion.md",
    "functions/Unified_Chat_入口设计与路由.md",
    "functions/Ops_Controlled_ReAct_Evidence_设计与实现.md",
    "eval/大模型与Agent开发工程师_项目面试问答.md",
    "agents/Contract_Agent_功能与流程.md",
    "agents/SqlLineage_Agent_功能与流程.md",
    "agents/HubGptAgent_功能与流程.md",
    "agents/MDM_Assistant_功能与流程.md",
    "functions/Query_Understanding_共享预处理设计与实现.md",
    "调优/RAG_Eval_and_Feedback_Tuning.md",
]


def copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        print(f"SKIP missing: {src}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"OK {dst.relative_to(ROOT)}")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for d in DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    for src_rel, dst_rel in OLD_MAP.items():
        copy_file(OLD / src_rel, ROOT / dst_rel)

    for src_rel, dst_rel in OBS_MAP.items():
        copy_file(OBS / src_rel, ROOT / dst_rel)

    for rel in GDS_FILES:
        src = GDS / rel
        safe = rel.replace("/", "__").replace("\\", "__")
        copy_file(src, ROOT / "06-原始资料-gds" / safe)

    resume_map = {
        "简历-田麟-6年经验-后端AI方向.md": "08-简历参考/简历-后端AI方向.md",
        "简历-田麟-6年-数据开发+ai.md": "08-简历参考/简历-数据开发+ai.md",
    }
    for src_name, dst_rel in resume_map.items():
        copy_file(RESUMES / src_name, ROOT / dst_rel)

    print("done.")


if __name__ == "__main__":
    main()
