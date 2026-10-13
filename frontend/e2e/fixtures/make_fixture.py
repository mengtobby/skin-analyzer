"""Generate a deterministic camera-free frame containing only geometric shapes."""
from pathlib import Path
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def make_frame() -> np.ndarray:
    """Return a 1280x720 BGR gradient with separated, non-facial polygons."""
    y, x = np.indices((720, 1280), dtype=np.int32)
    frame = np.stack((40 + x * 100 // 1279, 60 + y * 100 // 719,
                      30 + (x + y) * 60 // 1998), axis=-1).astype(np.uint8)
    cv2.rectangle(frame, (80, 100), (380, 300), (180, 100, 30), thickness=-1)
    triangle = np.array([[900, 120], [1150, 360], [750, 360]], dtype=np.int32)
    cv2.fillPoly(frame, [triangle], (90, 180, 40))
    cv2.rectangle(frame, (480, 520), (1080, 600), (150, 70, 50), thickness=-1)
    return frame


def main() -> None:
    output = Path(__file__).with_name("no-face.png")
    if not cv2.imwrite(str(output), make_frame(), [cv2.IMWRITE_PNG_COMPRESSION, 9]):
        raise OSError(f"Could not write fixture: {output}")
    logger.info("Wrote %s", output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
