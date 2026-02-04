# diagnostic_check.py
# =====================================================
# QUICK DIAGNOSTIC CHECK FOR TIMETABLE GENERATION
# =====================================================

import psycopg2
import os
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()

def get_connection():
    """Establish Supabase database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=os.getenv("SUPABASE_DB_PORT", "5432"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD")
    )

def check_database_state():
    """
    Run comprehensive diagnostics on database state
    Identifies potential issues before generation
    """
    
    print("=" * 80)
    print("TIMETABLE GENERATION - DATABASE DIAGNOSTICS")
    print("=" * 80)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # =====================================================
    # 1. TEACHER DAILY LIMITS
    # =====================================================
    print("\n📊 TEACHER DAILY LIMITS")
    print("-" * 80)
    cur.execute("""
        SELECT 
            teacher_id,
            teacher_name,
            max_lectures_per_day
        FROM teachers
        ORDER BY max_lectures_per_day, teacher_id
    """)
    
    limits = cur.fetchall()
    limit_distribution = defaultdict(int)
    
    for teacher_id, name, limit in limits:
        limit_distribution[limit] += 1
        if limit < 4:
            print(f"⚠️  Teacher {teacher_id} ({name}): Only {limit} lectures/day (LOW)")
    
    print(f"\nDaily Limit Distribution:")
    for limit, count in sorted(limit_distribution.items()):
        print(f"  {limit} lectures/day: {count} teachers")
    
    # =====================================================
    # 2. TEACHER WORKLOAD
    # =====================================================
    print("\n📚 TEACHER WEEKLY WORKLOAD")
    print("-" * 80)
    cur.execute("""
        SELECT 
            t.teacher_id,
            t.teacher_name,
            COALESCE(SUM(twl.weekly_theory_load), 0) as total_theory,
            COALESCE(SUM(twl.weekly_practical_load), 0) as total_practical,
            COALESCE(SUM(twl.weekly_theory_load), 0) + 
            COALESCE(SUM(twl.weekly_practical_load), 0) as total_hours
        FROM teachers t
        LEFT JOIN teacher_weekly_load twl ON twl.teacher_id = t.teacher_id
        GROUP BY t.teacher_id, t.teacher_name
        ORDER BY total_hours DESC
    """)
    
    workloads = cur.fetchall()
    
    print("Top 10 Teachers by Workload:")
    for i, (teacher_id, name, theory, practical, total) in enumerate(workloads[:10], 1):
        status = "⚠️ OVERLOADED" if total > 20 else "✅"
        print(f"{i:2}. Teacher {teacher_id:3} ({name:20}): {total:2}h/week (T:{theory:2}h P:{practical:2}h) {status}")
    
    avg_load = sum(w[4] for w in workloads) / len(workloads) if workloads else 0
    print(f"\nAverage teacher load: {avg_load:.1f} hours/week")
    
    overloaded = [w for w in workloads if w[4] > 20]
    if overloaded:
        print(f"⚠️  {len(overloaded)} teachers have >20 hours/week")
    
    # =====================================================
    # 3. SUBJECT ALLOCATIONS
    # =====================================================
    print("\n🎓 SUBJECT ALLOCATIONS")
    print("-" * 80)
    cur.execute("""
        SELECT 
            s.subject_id,
            s.subject_name,
            s.is_lab,
            COUNT(DISTINCT tsa.teacher_id) as theory_teachers,
            COUNT(DISTINCT tbsa.teacher_id) as lab_teachers
        FROM subjects s
        LEFT JOIN teacher_subject_allocation tsa ON tsa.subject_id = s.subject_id
        LEFT JOIN teacher_batch_subject_allocation tbsa ON tbsa.subject_id = s.subject_id
        GROUP BY s.subject_id, s.subject_name, s.is_lab
        ORDER BY s.subject_name
    """)
    
    allocations = cur.fetchall()
    
    issues = []
    for subj_id, name, is_lab, theory_teachers, lab_teachers in allocations:
        if is_lab and lab_teachers == 0:
            issues.append(f"⚠️  LAB subject '{name}' has NO batch allocations")
        elif not is_lab and theory_teachers == 0:
            issues.append(f"⚠️  THEORY subject '{name}' has NO teacher allocations")
    
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ All subjects have proper allocations")
    
    # =====================================================
    # 4. CLASS CONFIGURATION
    # =====================================================
    print("\n🏫 CLASS CONFIGURATION")
    print("-" * 80)
    cur.execute("""
        SELECT 
            c.class_id,
            c.class_name,
            COUNT(DISTINCT cb.batch_id) as num_batches
        FROM classes c
        LEFT JOIN class_batches cb ON cb.class_id = c.class_id
        GROUP BY c.class_id, c.class_name
        ORDER BY c.class_name
    """)
    
    classes = cur.fetchall()
    for class_id, name, batches in classes:
        print(f"  {name}: {batches} batches")
    
    # =====================================================
    # 5. WEEKLY LOAD CONFIGURATION
    # =====================================================
    print("\n⏰ WEEKLY LOAD REQUIREMENTS")
    print("-" * 80)
    cur.execute("""
        SELECT 
            slc.weekly_theory_load,
            slc.weekly_practical_load
        FROM subject_load_config slc
    """)
    
    loads = cur.fetchall()
    
    total_theory = sum(l[0] for l in loads)
    total_practical = sum(l[1] for l in loads)
    
    print(f"Total weekly theory hours required: {total_theory}")
    print(f"Total weekly practical hours required: {total_practical}")
    print(f"Total weekly hours required: {total_theory + total_practical}")
    
    # =====================================================
    # 6. CURRENT TIMETABLE STATE
    # =====================================================
    print("\n📅 CURRENT TIMETABLE STATE")
    print("-" * 80)
    cur.execute("""
        SELECT 
            day,
            COUNT(*) as entries
        FROM timetable
        GROUP BY day
        ORDER BY 
            CASE day
                WHEN 'Mon' THEN 1
                WHEN 'Tue' THEN 2
                WHEN 'Wed' THEN 3
                WHEN 'Thu' THEN 4
                WHEN 'Fri' THEN 5
            END
    """)
    
    timetable_state = cur.fetchall()
    
    if not timetable_state:
        print("  No timetable entries found")
    else:
        for day, count in timetable_state:
            print(f"  {day}: {count} entries")
        
        # Check if only Mon/Tue have entries
        days_with_entries = {day for day, count in timetable_state if count > 0}
        if days_with_entries <= {'Mon', 'Tue'}:
            print("\n⚠️  WARNING: Only Monday and Tuesday have entries!")
            print("  This suggests the generator is failing to place entries for later days.")
    
    # =====================================================
    # 7. POTENTIAL BOTTLENECKS
    # =====================================================
    print("\n🔍 POTENTIAL BOTTLENECKS")
    print("-" * 80)
    
    # Check teachers with high load but low daily limit
    cur.execute("""
        SELECT 
            t.teacher_id,
            t.teacher_name,
            t.max_lectures_per_day,
            COALESCE(SUM(twl.weekly_theory_load), 0) as weekly_theory
        FROM teachers t
        LEFT JOIN teacher_weekly_load twl ON twl.teacher_id = t.teacher_id
        GROUP BY t.teacher_id, t.teacher_name, t.max_lectures_per_day
        HAVING COALESCE(SUM(twl.weekly_theory_load), 0) > t.max_lectures_per_day * 2
        ORDER BY weekly_theory DESC
    """)
    
    bottlenecks = cur.fetchall()
    
    if bottlenecks:
        print("Teachers with high weekly load but low daily limit:")
        for teacher_id, name, daily_limit, weekly in bottlenecks:
            min_days_needed = weekly / daily_limit if daily_limit > 0 else 0
            print(f"  Teacher {teacher_id} ({name}): {weekly}h/week with {daily_limit} lectures/day limit")
            print(f"    → Needs {min_days_needed:.1f} days minimum (may cause scheduling conflicts)")
    else:
        print("✅ No obvious bottlenecks detected")
    
    # =====================================================
    # SUMMARY
    # =====================================================
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    
    warnings = 0
    
    if len([w for w in workloads if w[4] > 20]) > 0:
        print(f"⚠️  {len([w for w in workloads if w[4] > 20])} teachers overloaded (>20h/week)")
        warnings += 1
    
    if issues:
        print(f"⚠️  {len(issues)} subjects with allocation issues")
        warnings += 1
    
    if bottlenecks:
        print(f"⚠️  {len(bottlenecks)} teachers with potential scheduling bottlenecks")
        warnings += 1
    
    if days_with_entries and days_with_entries <= {'Mon', 'Tue'}:
        print("⚠️  Timetable only has entries for Mon/Tue - generation may be failing")
        warnings += 1
    
    if warnings == 0:
        print("✅ No major issues detected - database state looks healthy")
    else:
        print(f"\n⚠️  {warnings} potential issues detected - review above for details")
    
    print("=" * 80)
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_database_state()