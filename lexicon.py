# -*- coding: utf-8 -*-
"""
Từ điển thực thể (lexicon) cho miền bệnh đái tháo đường.

Mỗi entry có dạng  "Tên chuẩn (canonical)": [danh sách biến thể viết thường]
Biến thể được so khớp trên text đã lowercase, có ranh giới từ tiếng Việt.
Nhờ canonical hoá, "tiểu đường tuýp 2", "đái tháo đường type 2", "tiểu đường
loại 2"... đều gộp về CÙNG một node trong Knowledge Graph.
"""

DISEASES = {
    "Đái tháo đường type 1": [
        "đái tháo đường type 1", "đái tháo đường tuýp 1", "đái tháo đường típ 1",
        "đái tháo đường loại 1", "tiểu đường type 1", "tiểu đường tuýp 1",
        "tiểu đường típ 1", "tiểu đường loại 1", "đái tháo đường typ 1",
        "type 1", "tuýp 1", "típ 1",
    ],
    "Đái tháo đường type 2": [
        "đái tháo đường type 2", "đái tháo đường tuýp 2", "đái tháo đường típ 2",
        "đái tháo đường loại 2", "tiểu đường type 2", "tiểu đường tuýp 2",
        "tiểu đường típ 2", "tiểu đường loại 2", "đái tháo đường typ 2",
        "đái tháo đường không phụ thuộc insulin",
        "tiểu đường không phụ thuộc insulin",
        "type 2", "tuýp 2", "típ 2",
    ],
    "Đái tháo đường thai kỳ": [
        "đái tháo đường thai kỳ", "tiểu đường thai kỳ", "đái tháo đường thai nghén",
    ],
    "Tiền đái tháo đường": [
        "tiền đái tháo đường", "tiền tiểu đường", "prediabetes",
        "rối loạn dung nạp glucose",
    ],
    "Đái tháo đường ở trẻ em": [
        "đái tháo đường ở trẻ em", "tiểu đường ở trẻ em", "tiểu đường trẻ em",
    ],
    "Hạ đường huyết": [
        "hạ đường huyết", "hạ glucose máu", "tụt đường huyết",
    ],
    "Tăng đường huyết": [
        "tăng đường huyết", "đường huyết cao", "tăng glucose máu",
        "đường trong máu cao",
    ],
    # canonical tổng quát — chỉ dùng khi không khớp được thể bệnh cụ thể
    "Đái tháo đường": [
        "đái tháo đường", "tiểu đường", "bệnh tiểu đường", "bệnh đái tháo đường",
        "đtđ",
    ],
}

# Bệnh "chung"; nếu trong câu có thể bệnh cụ thể thì ưu tiên thể cụ thể
GENERIC_DISEASE = "Đái tháo đường"

SYMPTOMS = {
    "Khát nước nhiều": ["khát nước", "uống nhiều nước", "hay khát", "uống nhiều", "khô miệng"],
    "Đi tiểu nhiều": ["đi tiểu nhiều", "tiểu nhiều", "đái nhiều", "tiểu đêm", "tiểu nhiều lần"],
    "Sụt cân không rõ nguyên nhân": ["sụt cân", "giảm cân không rõ nguyên nhân", "gầy sút", "sút cân"],
    "Đói thường xuyên": ["đói thường xuyên", "ăn nhiều", "nhanh đói", "đói cồn cào", "thèm ăn"],
    "Mệt mỏi": ["mệt mỏi", "uể oải", "kiệt sức", "suy nhược"],
    "Mờ mắt": ["mờ mắt", "nhìn mờ", "thị lực giảm", "giảm thị lực", "mắt mờ"],
    "Tê bì chân tay": ["tê bì", "tê tay chân", "tê chân tay", "châm chích", "dị cảm", "tê rần"],
    "Chậm lành vết thương": ["chậm lành vết thương", "vết thương lâu lành", "vết thương chậm lành", "lâu lành"],
    "Ngứa da": ["ngứa da", "da ngứa", "khô da", "da khô", "ngứa ngáy"],
    "Nhiễm trùng tái phát": ["nhiễm trùng tái phát", "dễ nhiễm trùng", "nhiễm nấm tái phát", "hay bị nhiễm trùng"],
    "Buồn nôn": ["buồn nôn"],
    "Nôn": ["nôn ói", "nôn mửa"],
    "Đau đầu": ["đau đầu", "nhức đầu"],
    "Chóng mặt": ["chóng mặt", "hoa mắt"],
    "Vết thâm da (gai đen)": ["gai đen", "acanthosis nigricans", "sạm da vùng cổ"],
    "Rối loạn cương dương": ["rối loạn cương dương", "giảm ham muốn"],
    "Thở nhanh sâu": ["thở nhanh sâu", "thở kiểu kussmaul", "hơi thở mùi trái cây"],
}

LAB_TESTS = {
    "HbA1c": ["hba1c", "hb a1c", "a1c"],
    "Glucose huyết tương lúc đói": [
        "glucose huyết tương lúc đói", "đường huyết lúc đói", "glucose máu lúc đói",
        "đường huyết đói", "fasting glucose", "glucose lúc đói",
    ],
    "Nghiệm pháp dung nạp glucose (OGTT)": [
        "ogtt", "nghiệm pháp dung nạp glucose", "dung nạp glucose đường uống",
        "nghiệm pháp dung nạp",
    ],
    "Glucose máu bất kỳ": ["glucose máu bất kỳ", "đường huyết bất kỳ", "glucose huyết tương bất kỳ"],
    "Xét nghiệm đường huyết": ["xét nghiệm đường huyết", "đo đường huyết", "glucose máu", "đường huyết", "đường trong máu"],
    "Insulin máu": ["insulin máu", "định lượng insulin", "nồng độ insulin"],
    "C-peptide": ["c-peptide", "c peptide"],
    "Xét nghiệm nước tiểu": ["xét nghiệm nước tiểu", "albumin niệu", "microalbumin", "protein niệu", "ceton niệu", "đường niệu"],
    "Xét nghiệm lipid máu": ["lipid máu", "mỡ máu", "cholesterol máu", "triglyceride máu", "bộ mỡ máu"],
    "Creatinin máu": ["creatinin", "độ lọc cầu thận", "egfr"],
    "Soi đáy mắt": ["soi đáy mắt", "khám đáy mắt", "chụp đáy mắt"],
    "Xét nghiệm kháng thể tự miễn": ["kháng thể tự miễn", "anti-gad", "kháng thể kháng đảo tụy"],
}

RISK_FACTORS = {
    "Béo phì": ["béo phì", "obesity"],
    "Thừa cân": ["thừa cân", "dư cân", "bmi cao", "chỉ số bmi cao"],
    "Ít vận động": ["ít vận động", "lười vận động", "không tập thể dục", "lối sống tĩnh tại", "ít hoạt động thể chất"],
    "Tiền sử gia đình / di truyền": ["di truyền", "tiền sử gia đình", "người thân mắc", "yếu tố gen", "gia đình có người mắc"],
    "Tăng huyết áp": ["tăng huyết áp", "huyết áp cao", "cao huyết áp"],
    "Rối loạn lipid máu": ["rối loạn lipid máu", "cholesterol cao", "mỡ máu cao", "triglyceride cao", "rối loạn mỡ máu"],
    "Tuổi cao": ["tuổi cao", "lớn tuổi", "trên 45 tuổi", "tuổi tác", "người cao tuổi"],
    "Stress": ["stress", "căng thẳng"],
    "Chế độ ăn nhiều đường": ["ăn nhiều đường", "đồ ngọt", "nước ngọt", "thực phẩm nhiều đường", "chế độ ăn không lành mạnh", "ăn nhiều tinh bột"],
    "Hút thuốc lá": ["hút thuốc lá", "hút thuốc", "thuốc lá"],
    "Uống rượu bia": ["uống rượu bia", "rượu bia", "lạm dụng rượu"],
    "Tiền sử đái tháo đường thai kỳ": ["tiền sử đái tháo đường thai kỳ", "từng bị tiểu đường thai kỳ"],
    "Hội chứng buồng trứng đa nang": ["buồng trứng đa nang", "pcos"],
    "Kháng insulin": ["kháng insulin", "đề kháng insulin", "insulin resistance"],
    "Rối loạn giấc ngủ": ["ngưng thở khi ngủ", "rối loạn giấc ngủ", "mất ngủ"],
}

COMPLICATIONS = {
    "Bệnh thận đái tháo đường": ["bệnh thận đái tháo đường", "biến chứng thận", "tổn thương thận", "suy thận", "bệnh thận mạn"],
    "Bệnh võng mạc đái tháo đường": ["bệnh võng mạc đái tháo đường", "bệnh võng mạc", "biến chứng mắt", "tổn thương võng mạc", "võng mạc tiểu đường"],
    "Mù lòa": ["mù lòa", "mất thị lực", "mù vĩnh viễn"],
    "Bệnh thần kinh đái tháo đường": ["bệnh thần kinh đái tháo đường", "biến chứng thần kinh", "tổn thương thần kinh", "thần kinh ngoại biên", "bệnh lý thần kinh"],
    "Biến chứng tim mạch": ["biến chứng tim mạch", "bệnh tim mạch", "bệnh mạch vành", "xơ vữa động mạch", "suy tim"],
    "Nhồi máu cơ tim": ["nhồi máu cơ tim"],
    "Đột quỵ": ["đột quỵ", "tai biến mạch máu não"],
    "Loét bàn chân đái tháo đường": ["loét bàn chân", "bàn chân đái tháo đường", "bàn chân tiểu đường", "vết loét bàn chân", "hoại tử", "cắt cụt chi", "đoạn chi"],
    "Nhiễm toan ceton": ["nhiễm toan ceton", "toan ceton", "nhiễm toan xeton", "dka"],
    "Hôn mê tăng áp lực thẩm thấu": ["tăng áp lực thẩm thấu", "hôn mê tăng thẩm thấu"],
    "Hạ đường huyết": ["hạ đường huyết", "tụt đường huyết"],
    "Nhiễm trùng": ["nhiễm trùng da", "nhiễm trùng tiết niệu", "nhiễm trùng"],
    "Bệnh nha chu": ["bệnh nha chu", "viêm nướu", "viêm lợi"],
}

SIDE_EFFECTS = {
    "Buồn nôn": ["buồn nôn"],
    "Nôn": ["nôn", "nôn mửa"],
    "Tiêu chảy": ["tiêu chảy", "ỉa chảy"],
    "Đau bụng": ["đau bụng", "đau thượng vị", "khó chịu ở bụng"],
    "Chán ăn": ["chán ăn", "mất cảm giác ngon miệng"],
    "Táo bón": ["táo bón"],
    "Đầy hơi": ["đầy hơi", "đầy bụng", "chướng bụng", "đầy thượng vị"],
    "Ợ nóng": ["ợ nóng", "ợ chua"],
    "Rối loạn vị giác": ["rối loạn vị giác", "vị kim loại"],
    "Hạ đường huyết": ["hạ đường huyết", "hạ glucose huyết"],
    "Nhiễm toan lactic": ["nhiễm toan lactic", "toan lactic", "nhiễm acid lactic"],
    "Giảm vitamin B12": ["vitamin b12", "giảm hấp thu vitamin b12"],
    "Tăng cân": ["tăng cân"],
    "Phát ban": ["phát ban", "ban da", "ban đỏ"],
    "Mày đay": ["mày đay", "mề đay"],
    "Ngứa": ["ngứa"],
    "Nhạy cảm ánh sáng": ["cảm thụ với ánh sáng", "nhạy cảm ánh sáng"],
    "Thiếu máu": ["thiếu máu", "thiếu máu tan huyết", "thiếu máu bất sản"],
    "Giảm tiểu cầu": ["giảm tiểu cầu"],
    "Giảm bạch cầu": ["giảm bạch cầu", "mất bạch cầu hạt"],
    "Đau đầu": ["đau đầu", "nhức đầu"],
    "Chóng mặt": ["chóng mặt", "hoa mắt"],
    "Phù": ["phù ngoại biên", "phù nề", "phù"],
    "Viêm tụy cấp": ["viêm tụy"],
    "Đau khớp": ["đau khớp", "đau cơ"],
    "Nhiễm trùng đường tiết niệu": ["nhiễm trùng đường tiết niệu", "nhiễm khuẩn tiết niệu"],
    "Nhiễm nấm sinh dục": ["nhiễm nấm sinh dục", "nhiễm nấm bộ phận sinh dục", "viêm âm đạo do nấm"],
    "Phản ứng tại chỗ tiêm": ["phản ứng tại chỗ tiêm", "đau tại chỗ tiêm", "loạn dưỡng mô mỡ"],
    "Suy hô hấp": ["khó thở", "suy hô hấp"],
    "Rối loạn chức năng gan": ["tăng men gan", "viêm gan", "rối loạn chức năng gan"],
    "Sốc phản vệ": ["sốc phản vệ", "phản vệ"],
}

# Tác dụng phụ nguy hiểm -> severity = severe
SEVERE_SIDE_EFFECTS = {
    "Nhiễm toan lactic", "Sốc phản vệ", "Hạ đường huyết", "Viêm tụy cấp",
    "Suy hô hấp", "Thiếu máu", "Giảm bạch cầu", "Giảm tiểu cầu",
    "Rối loạn chức năng gan",
}
MODERATE_SIDE_EFFECTS = {
    "Nôn", "Tiêu chảy", "Phù", "Mày đay", "Phát ban", "Đau khớp",
    "Nhiễm trùng đường tiết niệu", "Nhiễm nấm sinh dục", "Giảm vitamin B12",
}

# Nhóm dược lý suy ra từ hoạt chất
DRUG_CLASSES = {
    "Biguanid (Metformin)": ["metformin"],
    "Sulfonylurea": ["gliclazid", "glimepirid", "glibenclamid", "glyburid", "glipizid", "tolbutamid", "clorpropamid"],
    "Ức chế DPP-4 (Gliptin)": ["sitagliptin", "vildagliptin", "linagliptin", "saxagliptin", "alogliptin"],
    "Ức chế SGLT2 (Gliflozin)": ["dapagliflozin", "empagliflozin", "canagliflozin", "ertugliflozin"],
    "Insulin": ["insulin", "glargin", "detemir", "degludec", "aspart", "lispro", "isophan", "glulisin"],
    "Thiazolidinedion": ["pioglitazon", "rosiglitazon"],
    "Ức chế alpha-glucosidase": ["acarbose", "voglibose", "miglitol"],
    "Đồng vận GLP-1": ["liraglutid", "semaglutid", "dulaglutid", "exenatid"],
    "Glinid": ["repaglinid", "nateglinid"],
    "Hormon tăng đường huyết": ["glucagon"],
}

# Hoạt chất dùng để nhận diện tương tác / chống chỉ định thuốc-thuốc
ACTIVE_INGREDIENTS = sorted(
    {name for names in DRUG_CLASSES.values() for name in names}
    | {"corticoid", "corticosteroid", "thuốc lợi tiểu", "furosemid",
       "thuốc cản quang", "cimetidin", "rifampicin", "warfarin",
       "thuốc ức chế men chuyển", "phenytoin", "salicylat"}
)

# Ngưỡng tham chiếu xét nghiệm (biên soạn theo ADA Standards of Care /
# Hướng dẫn chẩn đoán & điều trị ĐTĐ của Bộ Y tế) — dùng để làm giàu node
# :LabTest với các thuộc tính normal_range / unit vốn không có trên trang web.
LAB_REFERENCE = {
    "HbA1c":                              ("< 5.7 (bình thường); 5.7-6.4 (tiền ĐTĐ); >= 6.5 (chẩn đoán ĐTĐ)", "%"),
    "Glucose huyết tương lúc đói":        ("70-99 (bình thường); 100-125 (tiền ĐTĐ); >= 126 (chẩn đoán ĐTĐ)", "mg/dL"),
    "Nghiệm pháp dung nạp glucose (OGTT)": ("< 140 (bình thường); 140-199 (tiền ĐTĐ); >= 200 (chẩn đoán ĐTĐ) sau 2 giờ", "mg/dL"),
    "Glucose máu bất kỳ":                 (">= 200 kèm triệu chứng lâm sàng => chẩn đoán ĐTĐ", "mg/dL"),
    "Xét nghiệm đường huyết":             ("70-99 khi đói; < 140 sau ăn 2 giờ", "mg/dL"),
    "Insulin máu":                        ("2-25 khi đói", "µU/mL"),
    "C-peptide":                          ("0.5-2.0 khi đói", "nmol/L"),
    "Xét nghiệm nước tiểu":               ("Albumin niệu < 30 mg/g creatinin", "mg/g creatinin"),
    "Xét nghiệm lipid máu":               ("LDL-C < 100; HDL-C > 40 (nam) / > 50 (nữ); Triglycerid < 150", "mg/dL"),
    "Creatinin máu":                      ("0.6-1.2 (nam) / 0.5-1.1 (nữ); eGFR >= 60 mL/phút/1.73m2", "mg/dL"),
    "Soi đáy mắt":                        ("Không có tổn thương võng mạc", "định tính"),
    "Xét nghiệm kháng thể tự miễn":       ("Âm tính (dương tính gợi ý ĐTĐ type 1)", "định tính"),
}
