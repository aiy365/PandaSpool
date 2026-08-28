# PandaSpool Desk

任务栏托盘。悬停看打印进度、喷嘴/热床、空气；左键打开机台页；右键设置/退出。

WPF，请求在后台，不卡托盘。

## 运行

`pandaspool-desk.exe` 和 `pandaspool-desk.ini` 放一起。令牌用网站设置页的 **AI 令牌**。

设置里可开 **开机启动**、**打印结束通知**。刷新默认 30 秒；正在打印时自动改成最多 10 秒，进度环才跟得上。已经开着再双击，会提示「已经在托盘里」，并让原来那个弹出卡片。

若双击没反应：安装 [.NET 桌面运行时 10](https://dotnet.microsoft.com/zh-cn/download/dotnet/10.0)（Windows Desktop）。自包含发布见下面。

已经在运行再开一次，会提示「已经在托盘里」。

旧 Go 在 `legacy-win32/`，不要再用。

## 编译

框架依赖（小，本机已有运行时）：

```
cd src
dotnet publish -c Release -r win-x64 --self-contained false -p:PublishSingleFile=true -o ..\publish
```

拷给没装运行时的电脑：

```
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o ..\publish-full
```
