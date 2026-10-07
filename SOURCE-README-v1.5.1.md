# Codex Meter（本地适配版）

界面使用 macOS 原生 `NSVisualEffectView` 磨砂玻璃、圆角及系统柔和投影，无白色外框与紫色硬阴影，支持深色、浅色和跟随系统。

保留 [Claude-Meter](https://github.com/bonyuiux/Claude-Meter) 的小螃蟹、像素动画与悬浮窗口，连接本机 Codex。原版界面与设计 © 2026 Bon Yeung。原始版本：`0e6d7a05cec6e420f2c24164296a82d34096d1d3`，完整原版说明在 `UPSTREAM.md`。本适配版仅作本机使用，非 OpenAI 或 Anthropic 官方产品。

## 使用

小螃蟹动作跟随任务状态：进行中每 16 秒轮换打电脑、做饭、打网球、拍照和开飞机，点击动作区也可切换；等待回复或空闲时戴耳机听歌，本轮完成后撒花庆祝。额度、小螃蟹动画和单行任务导航合并在同一面板。左右箭头切换任务，所选任务保持固定，新到的待回复请求优先显示，点击名称打开对应 Codex task。系统开启「减少动态效果」时保留静态动作。

更新时间使用放大的中文「几秒前更新」。界面专注于桌面伴侣，原作致谢与版权说明保留在源代码注释和 `UPSTREAM.md` 中。

- 从「应用程序」打开 **Codex Meter**。可拖动、右键切换主题与紧凑模式。点「—」最小化，只保留小螃蟹和左上角额度；点小螃蟹恢复原来的面板。显示模式会记住。
- 每 60 秒通过官方 `codex app-server` 的 `account/rateLimits/read` 查询额度，显示账户实际返回的窗口及重置时间。点击刷新按钮可立即查询。
- 当前账户可能只有每周额度；不存在的数据不会显示为零或虚构出 5 小时窗口。
- 每 2 秒检查本机最近 60 个未归档主任务，面板顶部的一行导航显示进行中和等待回复的任务。左右箭头切换任务，序号显示当前位置，点击名称打开对应任务。所选任务保持固定；新到的待回复请求会优先显示。
- 任务本轮结束、出错或中断会显示任务通知；允许 macOS 通知后也会发系统通知。已有历史任务不会在启动时刷屏。
- 额度使用达到 80%、90%、100% 时提醒，同一额度窗口和阈值不重复提示。
- 右键「登录 Mac 时自动启动」可启用或关闭开机启动。「任务完成与额度通知」可关闭系统提醒，悬浮状态保留。

字符背景视觉参考：[Claude FM](https://www.youtube.com/watch?v=tRsQsTMvPNg)。新增开飞机忙碌场景：飞行帽、转动的螺旋桨和分层移动的雪山树林。飞行背景复用 [Tori Patterns Photo Lab](https://patterns.toritao.com/#/photo) 的亮度采样、字符密度与轮廓增强方式，从本地绘制的山景生成字符画。动画区域使用本地绘制的字符山景与细颗粒纹理，随场景切换暖沙、草绿和夜蓝色调。背景缓存后重复使用；跟随系统「减少动态效果」停止颗粒漂移。

## 数据的含义

**额度百分比**来自 Codex 账户，不是 API 充值余额，也不是剩余 token 数量。账户的具体计费与窗口定义以 Codex 官方为准。

**本轮完成**表示一次响应结束，不表示整个项目完成或成功。任务如提供 `update_plan`，会显示已完成计划步骤；没有数据时不会生成完成百分比。**tokens / 累计**是本机日志记录的该任务累计 token 使用量，缓存输入也可能计入，不能直接换算成费用。它不同于上下文窗口占用或账户剩余额度。

仅监控本机日志，不能覆盖其他电脑、纯云端任务或没有本地日志的聊天。后台内部审核及子代理不作为独立主任务展示。任务没有活动超过 30 分钟时显示「状态待确认」，不会假定完成。因本地日志格式可能随 Codex 升级而变化，之后可能需要调整读取逻辑。

同步 `request_user_input` 会显示等待回复；已成功提交的 `request_user_input_async` 会给仍在运行的任务标记「待回复」，匹配的回答或本轮结束会清除提示。异步提问不会被当成任务已暂停。待回复时也可发系统提醒。当前本地日志没有稳定提供所有权限审批弹窗，无法可靠提醒每一次 permission 请求；实际批准操作仍在 Codex 完成，不会自动批准或根据命令运行时间猜测权限状态。

## 隐私和运行方式

应用不调用模型，因此监控不会消耗模型 token。不读取或复制 API key、OAuth token 或钥匙串；登录由已安装的 Codex 官方可执行程序处理。仅调用初始化及额度只读接口，不创建、恢复、打断或修改 Codex 任务。

任务索引用 SQLite 只读模式打开，会读取任务名称和本地 JSONL 事件。不会上传任务日志或消息。界面没有远程字体依赖。额度缓存仅保存在 `~/Library/Application Support/Codex Meter/usage.json`，不含账户 ID、凭证或对话。

原版 Claude 安装脚本未运行；不会修改 Claude 设置或添加 Claude hooks。适配版的启动进程为应用、一个本地 Python 观察器，以及每次同步期间短暂启动的 Codex 官方进程。

## 构建和检查

需要 macOS 13+、Apple Command Line Tools（Swift 和 Python 3）及已登录的 Codex 应用。

```sh
python3 -m unittest -v test_bridge.py
node --test test_task_nav.cjs test_pet.cjs
./build.sh
```

构建输出：`/private/tmp/codex-meter-build/Codex Meter.app`（避免 iCloud 给应用包附加 Finder 元数据而影响签名）。

安装位置：`~/Applications/Codex Meter.app`。退出应用并关闭自动启动后，可删除这一个应用进行卸载；如需清除缓存，再删除 `~/Library/Application Support/Codex Meter`。不需要更改 Codex 或 Claude 配置。

全部活动共用同一套 Tori Patterns 字符风景渲染：打电脑是青灰林地，做饭是暖色丘陵，网球是草地缓坡，拍照是沙丘，飞机是雪山树林，听歌等待是月夜湖畔。仅调整地形和色调，字符密度、层次与光点风格保持一致；各场景背景缓存后复用。

## 场景预览与介绍素材

![Seven scenes with consistent character landscapes](media/scene-overview.png)

[七张独立缩略图](media/) · [视频分镜和中英文 X 文案草稿](release/LAUNCH-DRAFT.md)

当前已接入 Codex，其他 agent 尚未适配。
