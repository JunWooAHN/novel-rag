#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StyleSampler extra tests + CLI
"""

import sys
import json

import pytest

import data_modules.style_sampler as sampler_module
from data_modules.style_sampler import StyleSampler, StyleSample, SceneType
from data_modules.config import DataModulesConfig


@pytest.fixture
def temp_project(tmp_path):
    cfg = DataModulesConfig.from_project_root(tmp_path)
    cfg.ensure_dirs()
    return cfg


def test_style_sampler_more(temp_project):
    sampler = StyleSampler(temp_project)

    sample = StyleSample(
        id="ch1_s1",
        chapter=1,
        scene_type=SceneType.BATTLE.value,
        content="전투描写很精彩",
        score=0.9,
        tags=["전투"],
    )
    assert sampler.add_sample(sample) is True
    assert sampler.add_sample(sample) is False

    best = sampler.get_best_samples(limit=5)
    assert len(best) == 1

    stats = sampler.get_stats()
    assert stats["total"] == 1

    # scene type inference
    assert sampler._infer_scene_types("一场전투") == [SceneType.BATTLE.value]
    assert sampler._infer_scene_types("对话和谈话") == [SceneType.DIALOGUE.value]
    assert sampler._infer_scene_types("心理情感描写") == [SceneType.EMOTION.value]

    # classify and tags
    scene_type = sampler._classify_scene_type({"summary": "紧张", "content": ""})
    assert scene_type == SceneType.TENSION.value

    tags = sampler._extract_tags("전투 修炼 对话 描写")
    assert "전투" in tags


def test_style_sampler_cli(temp_project, monkeypatch, capsys):
    root = str(temp_project.project_root)

    def run_cli(args):
        monkeypatch.setattr(sys, "argv", ["style_sampler"] + args)
        sampler_module.main()

    run_cli(["--project-root", root, "stats"])
    run_cli(["--project-root", root, "list", "--limit", "5"])
    run_cli(
        [
            "--project-root",
            root,
            "extract",
            "--chapter",
            "1",
            "--score",
            "90",
            "--scenes",
            json.dumps(
                [
                    {
                        "index": 1,
                        "summary": "전투场景",
                        "content": "전투" + "a" * 300,
                    }
                ],
                ensure_ascii=False,
            ),
        ]
    )
    run_cli(["--project-root", root, "list", "--type", "전투", "--limit", "5"])
    run_cli(["--project-root", root, "select", "--outline", "本章有一场전투", "--max", "2"])

    capsys.readouterr()
