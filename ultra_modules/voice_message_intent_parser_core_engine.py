import re

def parse_voice_intent(text, default_intent="UNKNOWN"):
    """
    Parses a voice message text to extract user intent, entities, and confidence score.
    Includes zero-configuration auto-fault-tolerance (defaults, missing params)
    and silent dirty data cleaning (filler words, punctuation).
    """
    # 1. Edge cases and type checking (Zero-config auto-fallback)
    if text is None:
        return {"intent": default_intent, "entities": {}, "confidence": 0.0}

    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return {"intent": default_intent, "entities": {}, "confidence": 0.0}

    if not text.strip():
        return {"intent": default_intent, "entities": {}, "confidence": 0.0}

    # 2. Silently clean dirty data (filler words, punctuations)
    # Common filler words in Chinese voice messages
    filler_words = r'(呃|那个|这个|然后|就是|啊|呢|吧|嗯|哦|哈|啦|哎)'
    cleaned_text = re.sub(filler_words, '', text)
    # Remove common punctuations (both Chinese and English)
    cleaned_text = re.sub(r'[^\w\s]', '', cleaned_text).strip()

    if not cleaned_text:
        return {"intent": default_intent, "entities": {}, "confidence": 0.0}

    # 3. Rule-based intent extraction
    intent_scores = {
        "VERIFY_DOCUMENT": 0,
        "SCHEDULE_MEETING": 0,
        "LEAVE_REQUEST": 0
    }

    verify_keywords = ["核对", "核", "提成表", "报表", "文件", "审核", "核一下", "对一下", "核算"]
    meeting_keywords = ["开会", "会议", "开个会", "讨论", "拉个会", "碰一下", "碰个头", "开一会"]
    leave_keywords = ["请假", "休假", "事假", "病假", "年假", "调休", "请个假", "休息"]

    entities = {}

    # VERIFY_DOCUMENT scoring and entity extraction
    for kw in verify_keywords:
        if kw in cleaned_text:
            intent_scores["VERIFY_DOCUMENT"] += 1
            if kw in ["提成表", "报表", "文件", "工资单", "考勤表"]:
                entities["document_type"] = kw

    # SCHEDULE_MEETING scoring and entity extraction
    for kw in meeting_keywords:
        if kw in cleaned_text:
            intent_scores["SCHEDULE_MEETING"] += 1

    # LEAVE_REQUEST scoring and entity extraction
    for kw in leave_keywords:
        if kw in cleaned_text:
            intent_scores["LEAVE_REQUEST"] += 1
            if kw in ["事假", "病假", "年假", "调休"]:
                entities["leave_type"] = kw

    # General time extraction (simple)
    time_keywords = ["这月", "这个月", "下月", "下个月", "今天", "明天", "后天", "下周", "上午", "下午", "早上", "晚上"]
    for kw in time_keywords:
        if kw in cleaned_text:
            entities["time"] = kw
            break

    # Determine the most likely intent
    best_intent = default_intent
    max_score = 0

    for intent, score in intent_scores.items():
        if score > max_score:
            max_score = score
            best_intent = intent

    # Calculate a simple confidence score
    confidence = 0.0
    if max_score > 0:
        confidence = min(0.6 + 0.1 * max_score, 0.99)

    # If no intent matches, clear entities and reset
    if max_score == 0:
        best_intent = default_intent
        entities = {}
        confidence = 0.0

    return {
        "intent": best_intent,
        "entities": entities,
        "confidence": round(confidence, 2)
    }
