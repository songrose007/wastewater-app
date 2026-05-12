# GitHub 上传说明

第一版采用“生成成果包 + 手动 GitHub 上传命令”的安全方式，不在 WebUI 中保存 GitHub Token。

## 操作步骤

1. 在 WebUI 的“方案向导”中点击“生成成果包 ZIP”。
2. 下载成果包。
3. 在 GitHub 创建或准备好目标仓库。
4. 使用界面生成的命令上传：

```bash
git clone https://github.com/your-name/your-repo.git
cd your-repo
unzip 污水处理设计成果包_xxxxxxxx.zip
git add .
git commit -m "feat: add wastewater design project package"
git push
```

## 为什么不默认一键上传

一键上传需要处理 GitHub 凭据、分支权限和本地命令执行，存在安全风险。当前方式不会保存 token，也不会从 WebUI 后端执行任意 git 命令。

## 后续可选增强

如需要一键上传，可以后续增加：

```text
ENABLE_GITHUB_UPLOAD=false
```

只有显式开启后，后端才允许调用本地 `git` 或 `gh`，并且必须：

- 校验仓库 URL；
- 校验分支名；
- 禁止保存 token；
- 对日志脱敏；
- 只在受控导出目录执行命令。
