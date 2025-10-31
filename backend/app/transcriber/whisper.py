from faster_whisper import WhisperModel

from app.decorators.timeit import timeit
from app.models.transcriber_model import TranscriptSegment, TranscriptResult
from app.transcriber.base import Transcriber
from app.utils.env_checker import is_cuda_available
from app.utils.logger import get_logger
from app.utils.path_helper import get_model_dir

from events import transcription_finished
from pathlib import Path
import os
from tqdm import tqdm
from modelscope import snapshot_download


'''
 Size of the model to use (tiny, tiny.en, base, base.en, small, small.en, distil-small.en, medium, medium.en, distil-medium.en, large-v1, large-v2, large-v3, large, distil-large-v2, distil-large-v3, large-v3-turbo, or turbo
'''
logger=get_logger(__name__)

MODEL_MAP={
    "tiny": "pengzhendong/faster-whisper-tiny",
    'base':'pengzhendong/faster-whisper-base',
    'small':'pengzhendong/faster-whisper-small',
    'medium':'pengzhendong/faster-whisper-medium',
    'large-v1':'pengzhendong/faster-whisper-large-v1',
    'large-v2':'pengzhendong/faster-whisper-large-v2',
    'large-v3':'pengzhendong/faster-whisper-large-v3',
    'large-v3-turbo':'pengzhendong/faster-whisper-large-v3-turbo',
}

class WhisperTranscriber(Transcriber):
    # TODO:修改为可配置
    def __init__(
            self,
            model_size: str = "base",
            device: str = 'cuda',
            compute_type: str = None,
            cpu_threads: int = 1,
    ):
        requested_device = (device or 'cpu').lower()
        self.device = self._select_device(requested_device)
        if requested_device == 'cuda' and self.device != 'cuda':
            logger.info('未检测到可用的 CUDA 环境，自动回退为 CPU 推理')

        self.compute_type = compute_type or ("float16" if self.device == "cuda" else "int8")

        model_dir = get_model_dir("whisper")
        model_path = os.path.join(model_dir, f"whisper-{model_size}")
        if not Path(model_path).exists():
            logger.info(f"模型 whisper-{model_size} 不存在，开始下载...")
            repo_id = MODEL_MAP[model_size]
            model_path = snapshot_download(
                repo_id,

                local_dir=model_path,
            )
            logger.info("模型下载完成")

        self.model = WhisperModel(
            model_size_or_path=model_path,
            device=self.device,
            compute_type=self.compute_type,
            download_root=model_dir
        )

    @staticmethod
    def _select_device(requested_device: str) -> str:
        """根据用户请求与运行环境选择推理设备。"""
        if requested_device in (None, 'cpu'):
            return 'cpu'

        if requested_device == 'cuda':
            if is_cuda_available():
                logger.info('检测到 CUDA，可使用 GPU 推理')
                return 'cuda'
            logger.warning('请求使用 CUDA，但当前环境缺少 GPU 或相关依赖，回退至 CPU')
            return 'cpu'

        logger.warning(f'未知的推理设备 "{requested_device}"，默认使用 CPU')
        return 'cpu'

    @timeit
    def transcript(self, file_path: str) -> TranscriptResult:
        try:

            segments_raw, info = self.model.transcribe(file_path)

            segments = []
            full_text = ""

            for seg in segments_raw:
                text = seg.text.strip()
                full_text += text + " "
                segments.append(TranscriptSegment(
                    start=seg.start,
                    end=seg.end,
                    text=text
                ))

            result= TranscriptResult(
                language=info.language,
                full_text=full_text.strip(),
                segments=segments,
                raw=info
            )
            # self.on_finish(file_path, result)
            return result
        except Exception as e:
            print(f"转写失败：{e}")


    def on_finish(self,video_path:str,result: TranscriptResult)->None:
        print("转写完成")
        transcription_finished.send({
            "file_path": video_path,
        })
