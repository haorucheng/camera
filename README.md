# Camera Studio

一个基于 Python、Tkinter、OpenCV 和 Pillow 的桌面相机程序，支持：

- 调用电脑内置摄像头并实时预览
- 拍照并自动保存为高质量 JPG
- 最近照片列表与照片预览
- 删除照片、打开保存文件夹、切换保存目录
- 摄像头编号、分辨率、水平镜像设置
- `Space` 或 `Ctrl+S` 快捷拍照

## 运行

建议使用 Python 3.10 或更高版本，在 PowerShell 中执行：

```powershell
python -m pip install -r requirements.txt
python camera_studio.py
```

首次运行时，如果 Windows 弹出摄像头权限提示，请选择允许。默认照片目录为：
`C:\Users\\你的用户名\\Pictures\\CameraStudio`。

如果程序提示无法打开摄像头，请检查其他软件是否占用了摄像头，并在 Windows 的“设置 → 隐私和安全性 → 摄像头”中允许桌面应用访问摄像头。
