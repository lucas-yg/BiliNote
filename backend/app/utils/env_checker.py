def is_cuda_available() -> bool:
    """检测当前环境是否存在可用的 CUDA 设备。

    优先尝试使用 ctranslate2 检测 GPU 能力，因为 faster-whisper 基于该库。
    若环境未安装 ctranslate2，则回退到 torch 的可选检测逻辑。
    """
    try:
        import ctranslate2

        # ctranslate2 在无 CUDA 支持的构建下会返回 0，而不是抛错
        return ctranslate2.get_device_count("cuda") > 0
    except ImportError:
        pass
    except Exception:
        # 捕获其它异常，避免在启动阶段打断流程
        return False

    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
    except Exception:
        return False

def is_torch_installed() -> bool:
    try:
        import torch
        return True
    except ImportError:
        return False
