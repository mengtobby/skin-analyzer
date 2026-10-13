"""MediaPipe Face Mesh (478-point) landmark index sets used for zoning.

Derived from ``mediapipe.tasks.python.vision.FaceLandmarksConnections``; inlined so the
geometry code is importable and testable without MediaPipe.
"""

FACE_OVAL = (10, 21, 54, 58, 67, 93, 103, 109, 127, 132, 136, 148, 149, 150, 152, 162,
             172, 176, 234, 251, 284, 288, 297, 323, 332, 338, 356, 361, 365, 377, 378,
             379, 389, 397, 400, 454)
LEFT_EYE = (249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466)
RIGHT_EYE = (7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246)
LEFT_EYEBROW = (276, 282, 283, 285, 293, 295, 296, 300, 334, 336)
RIGHT_EYEBROW = (46, 52, 53, 55, 63, 65, 66, 70, 105, 107)
LIPS = (0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181,
        185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402,
        405, 409, 415)
NOSE = (1, 2, 4, 5, 6, 19, 45, 48, 64, 94, 97, 98, 115, 168, 195, 197, 220, 275, 278, 294,
        326, 327, 344, 440)

# Lower nose: alae, nostril bases and columella. Nostril openings and alar creases are
# deep, round shadows that a contrast detector cannot tell from pigmented spots
# (measured: the dominant source of false hyperpigmentation on real webcam frames).
NOSTRILS = (2, 19, 48, 64, 94, 97, 98, 278, 294, 326, 327)

RIGHT_EYE_OUTER = 33
LEFT_EYE_OUTER = 263
RIGHT_EYE_INNER = 133
LEFT_EYE_INNER = 362
NOSE_TIP = 1
MOUTH_RIGHT = 61
MOUTH_LEFT = 291
LOWER_LIP_BOTTOM = 17
CHIN = 152

NUM_LANDMARKS = 478
