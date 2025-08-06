#!/usr/bin/env python3

from AI_firebase import get_all_batches, get_all_students

def test_batch_summary():
    batches = get_all_batches()
    students = get_all_students()
    
    print(f"Found {len(batches)} batches and {len(students)} students")
    
    batch_summary = []
    for batch in batches:
        batch_id = batch['_id']
        batch_display_name = f"{batch.get('batch_name', 'Unknown')} ({batch.get('start_time', 'Unknown')}-{batch.get('end_time', 'Unknown')}) ({batch.get('batch_start_date', 'Unknown')})"
        
        # Count students in this batch
        batch_students = [s for s in students if s.get('batch_id') == batch_id]
        total_students = len(batch_students)
        
        # Count paid and unpaid students
        paid_students = len([s for s in batch_students if s.get('fees_status') == 'Paid'])
        unpaid_students = total_students - paid_students
        
        batch_summary.append({
            'batch_name': batch_display_name,
            'total_students': total_students,
            'paid_students': paid_students,
            'unpaid_students': unpaid_students
        })
    
    # Sort batch summary by batch name
    batch_summary.sort(key=lambda x: x['batch_name'])
    
    print("\nBatch Summary:")
    print("-" * 100)
    print(f"{'Batch Name':<50} {'Total':<10} {'Paid':<10} {'Unpaid':<10}")
    print("-" * 100)
    
    for batch in batch_summary:
        print(f"{batch['batch_name']:<50} {batch['total_students']:<10} {batch['paid_students']:<10} {batch['unpaid_students']:<10}")
    
    return batch_summary

if __name__ == "__main__":
    test_batch_summary()
