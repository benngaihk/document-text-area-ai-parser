"""
调试脚本：查看字段和附近标签的详细信息
"""
import json
from enhanced_form_parser import EnhancedFormParser

def debug_field_labels(pdf_path: str, target_field_names: list):
    """调试特定字段的标签匹配"""
    parser = EnhancedFormParser(pdf_path)
    enhanced_result = parser.enhance_fields_with_labels()

    for field in enhanced_result["fields"]:
        if field["fieldName"] not in target_field_names:
            continue

        print(f"\n{'='*80}")
        print(f"字段: {field['fieldName']} ({field['fieldType']})")
        print(f"{'='*80}")

        # 只看第一页的实例
        for instance in field["instances"]:
            if instance.get("pageNumber") == 1:
                print(f"\n页面: {instance['pageNumber']}")
                print(f"位置 (normalized): {instance.get('normalizedRect', {})}")
                print(f"\n附近的标签 (前20个):")
                print(f"{'距离':<10} {'X位置':<10} {'Y位置':<10} {'文本':<30}")
                print("-" * 80)

                field_rect = instance.get("normalizedRect", {})
                field_center_y = (field_rect.get("y1", 0) + field_rect.get("y2", 0)) / 2
                field_left_x = field_rect.get("x1", 0)

                print(f"字段中心 Y: {field_center_y:.4f}, 字段左侧 X: {field_left_x:.4f}\n")

                for i, label in enumerate(instance.get("nearbyLabels", [])[:20]):
                    distance = label["distance"]
                    bbox = label.get("boundingBox", {})
                    label_x = (bbox.get("x1", 0) + bbox.get("x2", 0)) / 2
                    label_y = (bbox.get("y1", 0) + bbox.get("y2", 0)) / 2
                    text = label["text"].replace("\n", " ")[:30]

                    # 标记是否在左侧且水平对齐
                    is_left = "←" if label_x < field_left_x else "→"
                    is_aligned = "✓" if abs(label_y - field_center_y) < 0.02 else " "

                    print(f"{distance:<10.4f} {label_x:<10.4f} {label_y:<10.4f} {is_left}{is_aligned} {text:<30}")
                break

if __name__ == "__main__":
    # 调试特定字段
    target_fields = [
        "fill_9_P",   # 应该是"建議採用的公司英文名稱"
        "fill_10_P",  # 应该是"建議採用的公司英文名稱"
        "fill_11_P",  # 应该是"建議採用的公司中文名稱"
        "fill_12_P"   # 应该是"建議採用的公司中文名稱"
    ]

    debug_field_labels("NNC1_fillable.pdf", target_fields)
