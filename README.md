# Noto Sans Akira

Noto Sans Akira 是一套用于桌面界面的西文字体。英文字母、数字和已有的拉丁、希腊、西里尔字形来自 Noto Sans CJK SC。字体保留原有英文轮廓和字重，并为西文标点提供比例宽度。

## 字重

| 字重 | 数值 | 文件 |
| --- | ---: | --- |
| Thin | 100 | `fonts/NotoSansAkira-Thin.otf` |
| Light | 300 | `fonts/NotoSansAkira-Light.otf` |
| DemiLight | 350 | `optional/NotoSansAkira-DemiLight.otf` |
| Regular | 400 | `fonts/NotoSansAkira-Regular.otf` |
| Medium | 500 | `fonts/NotoSansAkira-Medium.otf` |
| Bold | 700 | `fonts/NotoSansAkira-Bold.otf` |
| Black | 900 | `fonts/NotoSansAkira-Black.otf` |

字体包含六个默认安装的静态字重和一个可选 DemiLight 字重，没有独立的斜体文件。打开 `preview.html` 可以预览全部七个字重和中英文混排。

Firefox 157 在 Linux 原生字体匹配中将 300 和 350 都映射为 300。同一字族同时安装 Light 和 DemiLight 时，可能把 Light 请求匹配到 DemiLight。默认安装命令只复制 `fonts/` 中的六个标准字重；`optional/` 中的 DemiLight 可用于显式 `@font-face` 引用，或按应用需求单独安装。此限制不影响字体文件中保存的 350 字重信息。参见 [Firefox 字重映射](https://github.com/mozilla-firefox/firefox/blob/main/gfx/thebes/gfxFcPlatformFontList.cpp)。

## 标点与回退

ASCII 标点保留原有比例宽度。弯引号、中点和圆点使用 CJK SC 内置的比例字形。部分数学符号、西文标点和特殊空格采用 Noto Sans 的字形或间距。

同一码点的弯引号在中文和英文中均采用西文宽度。汉字、假名、韩文、中文专用标点、专用图标和 Emoji 由其他字体提供。推荐安装 Noto Sans、Noto Sans CJK SC、Noto Sans Symbols、Noto Sans Symbols 2 和 Noto Color Emoji。

## 安装

### Arch Linux

`noto-sans-akira` 由 [AkiraLyu/pkgbuilds](https://github.com/AkiraLyu/pkgbuilds) 提供。将该仓库加入 paru 配置后运行：

```bash
paru --sudo run0 -S noto-sans-akira
```

包安装六个默认字重，并依赖 Noto Sans、Noto Sans CJK SC 和 Noto Color Emoji 所在的包。DemiLight 保存在 `/usr/share/noto-sans-akira/optional/`，不会参与系统字体匹配。

包默认启用 Fontconfig 配置，统一 `sans-serif`、`system-ui` 和符号回退。配置文件安装到 `/usr/share/fontconfig/conf.avail/61-noto-sans-akira.conf`，默认链接由 Arch Linux 的 Fontconfig 安装钩子同步到 `/etc/fonts/conf.d/`。安装或升级后重启浏览器。

配置保留应用显式指定的字体及等宽字体选择。已有用户配置若为 `sans-serif` 或 `system-ui` 强制指定其他字体，应移除这些重复默认规则，由字体包统一提供默认回退。

### 手动安装

在解压后的目录中运行：

```bash
mkdir -p "$HOME/.local/share/fonts/NotoSansAkira"
cp fonts/*.otf "$HOME/.local/share/fonts/NotoSansAkira/"
fc-cache -f "$HOME/.local/share/fonts/NotoSansAkira"
```

将 KDE 和 GTK 的界面字体设置为 `Noto Sans Akira`。字体名称只替换西文部分；中文字符使用字体回退。

Fontconfig 配置将 `sans-serif` 和 `system-ui` 的首选字体设置为 Noto Sans Akira，并补充字符回退。此配置不修改等宽字体。手动安装字体时，可按以下命令部署配置，然后重启浏览器：

```bash
mkdir -p "$HOME/.config/fontconfig/conf.d"
cp fontconfig/61-noto-sans-akira.conf "$HOME/.config/fontconfig/conf.d/"
```

Firefox 和 Chrome 的 `system-ui` 还会读取各自使用的 GTK 或 Qt 界面字体。因此，应将相关工具包的字体也设置为 `Noto Sans Akira`。字体不能将原本输入为全角码点的字符转换成 ASCII。

## 构建

需要 Python 3 和 FontTools。默认读取 Arch Linux 的 `noto-fonts-cjk`、`noto-fonts` 字体路径：

```bash
python3 tools/build.py
```

其他字体目录可通过 `--cjk-dir`、`--latin-dir` 指定。构建过程保留 CJK SC 的西文轮廓及垂直度量，提取所需字符，并删除东亚语言及全角宽度替换特性。符号补充规则见 [来源](docs/attribution.md)。

## 许可

字体采用 [SIL Open Font License 1.1](docs/LICENSE.md)。原始字形的版权归原作者所有。分发字体时应保留许可及版权信息。
