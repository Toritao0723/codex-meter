# Codex Meter · v1.3.0 私有备份

当前桌面安装版本的完整快照：**1.3.0 / build 6**，macOS Apple Silicon。备份创建于 2026-10-08（Asia/Hong_Kong）。

功能包括原生磨砂玻璃界面、Codex 实际账户额度、紧凑的小螃蟹动作、右对齐的独立任务通知列表、明确的待回复提醒。权限审批弹窗目前不能可靠检测，具体限制记录在完整源码包的 README 中。

## 备份文件

- [完整源码与应用备份](Codex-Meter-v1.3.0-complete-backup.zip)：保持目录结构的源码、构建脚本、测试、原作说明和应用包，共 17 个文件。
- [直接恢复 macOS 应用](Codex-Meter-v1.3.0-macOS-arm64.zip)：备份时已安装的 `Codex Meter.app`。
- [Git 版本历史](Codex-Meter-v1.3.0-backup.bundle)：本地仓库与 `v1.3.0` 标签，源码提交 `32d2f858e13e98865fdb83985744b2fcc5361eff`。
- [版本与源码校验清单](v1.3.0-manifest.json) 和 [下载文件校验值](SHA256SUMS.txt)。

此仓库以可恢复的归档文件保存原始目录和 Git 历史；GitHub 上的归档提交与包内源码提交分别保存。

## 恢复

直接使用：退出正在运行的 Codex Meter，解压 macOS 应用包，将 `Codex Meter.app` 放回 `~/Applications/`。本地临时签名可能需要在新机器重新构建。

恢复源码：下载并解压完整备份，进入 `Codex-Meter-v1.3.0` 目录。构建前需要 Apple Command Line Tools，运行：

```sh
python3 -m unittest -v test_bridge.py
./build.sh
```

构建结果在 `/private/tmp/codex-meter-build/Codex Meter.app`。首次使用需在本机 Codex 登录；备份不含登录凭据。

恢复 Git 仓库：下载 `.bundle` 文件后运行：

```sh
git clone Codex-Meter-v1.3.0-backup.bundle codex-meter-source
cd codex-meter-source
git checkout v1.3.0
```

## 来源与隐私

基于 [Bon Yeung 的 Claude-Meter](https://github.com/bonyuiux/Claude-Meter)，原始版本 `0e6d7a05cec6e420f2c24164296a82d34096d1d3`。原版界面与像素角色 © 2026 Bon Yeung；完整署名与原版说明保留在 [UPSTREAM.md](UPSTREAM.md)。本项目为个人 Codex 适配备份，非 OpenAI 或 Anthropic 官方产品。

未包含 API key、登录凭据、使用量缓存、Codex 任务日志或个人应用偏好。
