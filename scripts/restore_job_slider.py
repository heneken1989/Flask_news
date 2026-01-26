#!/usr/bin/env python3
"""
Script để restore lại job slider sau khi test
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app
from database import db, Article


def restore_job_slider():
    """Restore job slider (set is_home=True)"""
    print("="*80)
    print("🔄 RESTORE JOB SLIDER")
    print("="*80)
    print()
    
    with app.app_context():
        # Tìm job slider ở row 19 (display_order=19000)
        job_slider = Article.query.filter_by(
            layout_type='job_slider',
            display_order=19000,
            language='da'
        ).first()
        
        if job_slider:
            print(f"✅ Tìm thấy job slider (ID: {job_slider.id})")
            print(f"   Current is_home: {job_slider.is_home}")
            print()
            
            if not job_slider.is_home:
                job_slider.is_home = True
                db.session.commit()
                print("✅ Đã restore job slider (set is_home=True)")
            else:
                print("ℹ️  Job slider đã có is_home=True, không cần restore")
        else:
            print("❌ Không tìm thấy job slider với display_order=19000")
        
        print()


if __name__ == '__main__':
    restore_job_slider()

