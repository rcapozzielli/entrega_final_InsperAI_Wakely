"""Perguntas fixas feitas ao Laya (protocolo do Laya). O checkpoint base é em inglês, então o texto vai em inglês.

Fixadas em 13/11/2026, antes de qualquer previsão nas janelas rotuladas; não mudam depois.
"""
ESTADO = {"estado": {
    "type": "choice",
    "instructions": ("The state is a 2-second summary of a driver's face from a camera: eye-closure probability, "
                     "longest eye-closure in seconds, eye aspect ratio relative to the driver's own open eye, mouth "
                     "opening, yawn flag, head pitch and yaw relative to the start, and how much the eyes look down. "
                     "What is the driver doing?"),
    "criteria": {"normal": "awake and looking at the road",
                 "distraido": "eyes open but looking down or to the side (phone, reading, reaching for an object)",
                 "microssono": "eyes closed for one second or more (microsleep)"}}}

ALARME = {"alarme": {
    "type": "choice",
    "instructions": "Using the same 2-second summary of the driver's face, should the microsleep alarm sound now?",
    "criteria": {"nao": "no, the driver is not asleep", "sim": "yes, the eyes have been closed for one second or more"}}}

ROTULOS = ["normal", "distraido", "microssono"]
