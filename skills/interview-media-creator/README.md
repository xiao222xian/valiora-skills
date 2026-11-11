# 采访短片 · Interview Short（lov-interview-media-creator）

![Version](https://img.shields.io/badge/version-0.6.0-CC785C)

把一场采访录像剪成 2–4 分钟（最长约 4 分钟）的视频号竖版采访短片：被访者原话做冷开场，重排成约 5 章，提问卡与回答字幕分开，
人名条、讲解图形、跳切推近、按内容生成的配乐、合影与官方 Logo 收尾，封面出 A/B 两版，选定后配一张 4:3 分享卡。`lov-film` 片型套件成员；
混音与质检调用 `lov-media-creator`，发布交给 `lov-media-publisher`。横版深度访谈、访谈长片与访谈纪录片用 `lov-media-creator`
narrative-vlog「访谈长片」；多人圆桌要剪映草稿或批量选题用 `lov-roundtable-clip`。

## 安装

包含在 Lovstudio.AI VIP Membership 全套权益中；会员账号登录后安装：

```bash
npx lovstudio skills add interview-media-creator -g -y
```

安装时会一并装上依赖 `lov-media-creator`（混音、母带与音频质检脚本，同在会员权益中）和 `lov-branding-consistency`。
`lov-media-creator` 装在别处时，设 `MEDIA_CREATOR_DIR` 指向它的目录。

## 用法示例

- 「刚采访了一位创业者，看本文件夹的视频和微信聊天记录『某某』，做一个适合发视频号的采访视频，要尽可能爆」
  → 审片版竖版成片、审片字幕、封面 A/B、发布文案、导演阐述与交付报告；确认后交发布。
- 「这位新朋友的采访也剪一条，可以用她的公众号和朋友圈自述补背景」
  → 同上，公众号与自述的事实写进事实台账，字幕仍只用采访原话。
- 「这条采访短片从专业导演角度重新策划一版」→ 先交导演阐述，批准后重剪。
- 视频号发完，B 站也要一条 → 从同一条时间线派生 16:9 横版（剪辑、字幕、混音不动）、16:9 封面与 B 站文案，交给 `lov-media-publisher`；
  发布方 Profile 里 B 站登记为自动发布时不再问作者。

## Profile

在 `skill.yaml` 中声明 `user-profile/v1`：读取品牌名与官方 Logo、工作区，以及本 Skill 的记录（系列名、章节卡时长、语速、是否美颜、
字体、默认平台）。作者直接说出的长期偏好立即写回，例如：

```bash
python3 scripts/profile_store.py record --skill-id lov-interview-media-creator --path records.beauty --value false --confirm
```

详见 [`references/user-profile.md`](references/user-profile.md)。

## 依赖

- Python 3.9+（持久虚拟环境）：numpy、opencv-python、mlx-whisper、opencc、jieba
- 第一次转写会从 Hugging Face 下载 `mlx-community/whisper-large-v3-mlx`（约 3.1 GB）与 `mlx-community/whisper-large-v3-turbo`（约 1.6 GB）；
  两个都缓存后可设 `HF_HUB_OFFLINE=1`；缓存被清理后的离线重建见 `SKILL.md` Step 0
- FFmpeg / FFprobe（含 zscale）、Node 20+、Remotion 4；macOS `avconvert`（杜比视界素材转 SDR 源，`scripts/sdr_source.py`）
- OpenCV YuNet 人脸模型：从 OpenCV model zoo 下载
  [`face_detection_yunet_2023mar.onnx`](https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx)，
  放到 `~/models/yunet.onnx` 或用 `YUNET_MODEL` / `--yunet` 指定；macOS `swiftc`
- `lov-media-creator`（必需）、`lov-branding-consistency`；可选 `lov-media-publisher`、`lov-wdb-cli`、`lov-channels-cover`
- 可选 `OPENROUTER_API_KEY`（Lyria 配乐）

## 质量门禁

```bash
python3 scripts/validate_skill.py .
```

脚本的 `--help` 需在装好依赖的虚拟环境里运行。可信度记录：`skill-card.yaml` / `skill-card.md`、`cases/cases.json`、`pricing-card.yaml`；
组合决策：`references/skill-composition.md`。

## License

MIT
