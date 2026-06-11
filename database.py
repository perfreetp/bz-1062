import sqlite3
import os
import shutil
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'green_management.db')
PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'photos')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'backups')


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(PHOTO_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS plants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        species TEXT,
        spec TEXT,
        quantity INTEGER DEFAULT 1,
        area REAL DEFAULT 0,
        position_x REAL DEFAULT 0,
        position_y REAL DEFAULT 0,
        area_name TEXT,
        responsible TEXT,
        status TEXT DEFAULT '正常',
        plant_date TEXT,
        notes TEXT,
        is_deleted INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS maintenance_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_id INTEGER,
        plan_type TEXT NOT NULL,
        frequency_days INTEGER DEFAULT 7,
        last_date TEXT,
        next_date TEXT,
        responsible TEXT,
        notes TEXT,
        is_deleted INTEGER DEFAULT 0,
        FOREIGN KEY (plant_id) REFERENCES plants(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS maintenance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER,
        plant_id INTEGER,
        record_type TEXT NOT NULL,
        record_date TEXT NOT NULL,
        operator TEXT,
        result TEXT,
        notes TEXT,
        FOREIGN KEY (plant_id) REFERENCES plants(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_id INTEGER,
        file_path TEXT NOT NULL,
        upload_date TEXT DEFAULT (datetime('now','localtime')),
        shot_date TEXT,
        description TEXT,
        FOREIGN KEY (plant_id) REFERENCES plants(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_type TEXT NOT NULL,
        amount REAL NOT NULL,
        expense_date TEXT NOT NULL,
        vendor TEXT,
        contract_end_date TEXT,
        related_plant_id INTEGER,
        notes TEXT,
        FOREIGN KEY (related_plant_id) REFERENCES plants(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS backup_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        backup_date TEXT DEFAULT (datetime('now','localtime')),
        description TEXT,
        record_count INTEGER
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        category TEXT NOT NULL,
        area_name TEXT,
        budget_amount REAL NOT NULL,
        notes TEXT
    )''')

    c.execute("PRAGMA table_info(photos)")
    columns = [col[1] for col in c.fetchall()]
    if 'shot_date' not in columns:
        c.execute("ALTER TABLE photos ADD COLUMN shot_date TEXT")
    if 'abnormal_status' not in columns:
        c.execute("ALTER TABLE photos ADD COLUMN abnormal_status TEXT DEFAULT '无异常'")

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='budgets'")
    if not c.fetchone():
        c.execute('''CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            category TEXT NOT NULL,
            area_name TEXT,
            budget_amount REAL NOT NULL,
            notes TEXT
        )''')

    c.execute('''CREATE TABLE IF NOT EXISTS plant_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_id INTEGER NOT NULL,
        old_status TEXT,
        new_status TEXT NOT NULL,
        change_date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (plant_id) REFERENCES plants(id)
    )''')

    c.execute("SELECT COUNT(*) FROM plant_status_history")
    if c.fetchone()[0] == 0:
        c.execute("SELECT id, status, created_at FROM plants WHERE is_deleted = 0")
        plants = c.fetchall()
        for p in plants:
            change_date = p['created_at'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('''INSERT INTO plant_status_history 
                        (plant_id, old_status, new_status, change_date, notes)
                        VALUES (?, ?, ?, ?, ?)''',
                      (p['id'], None, p['status'], change_date, '初始状态'))

    conn.commit()
    conn.close()


class PlantManager:
    @staticmethod
    def get_all(keyword=None, status=None, area_name=None):
        conn = get_conn()
        c = conn.cursor()
        query = "SELECT * FROM plants WHERE is_deleted = 0"
        params = []
        if keyword:
            query += " AND (name LIKE ? OR species LIKE ? OR responsible LIKE ?)"
            params.extend([f'%{keyword}%'] * 3)
        if status:
            query += " AND status = ?"
            params.append(status)
        if area_name:
            query += " AND area_name = ?"
            params.append(area_name)
        query += " ORDER BY id DESC"
        rows = c.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(plant_id):
        conn = get_conn()
        c = conn.cursor()
        row = c.execute("SELECT * FROM plants WHERE id = ?", (plant_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def add(data):
        conn = get_conn()
        c = conn.cursor()
        status = data.get('status', '正常')
        c.execute('''INSERT INTO plants (name, species, spec, quantity, area, 
                    position_x, position_y, area_name, responsible, status, plant_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data.get('name'), data.get('species'), data.get('spec'),
                   data.get('quantity', 1), data.get('area', 0),
                   data.get('position_x', 0), data.get('position_y', 0),
                   data.get('area_name'), data.get('responsible'),
                   status, data.get('plant_date'),
                   data.get('notes')))
        plant_id = c.lastrowid
        change_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO plant_status_history 
                    (plant_id, old_status, new_status, change_date, notes)
                    VALUES (?, ?, ?, ?, ?)''',
                  (plant_id, None, status, change_date, '初始状态'))
        conn.commit()
        conn.close()
        return plant_id

    @staticmethod
    def update(plant_id, data):
        conn = get_conn()
        c = conn.cursor()
        old_plant = c.execute("SELECT status FROM plants WHERE id = ?", (plant_id,)).fetchone()
        old_status = old_plant['status'] if old_plant else None
        fields = []
        params = []
        for key in ['name', 'species', 'spec', 'quantity', 'area',
                    'position_x', 'position_y', 'area_name', 'responsible',
                    'status', 'plant_date', 'notes']:
            if key in data:
                fields.append(f"{key} = ?")
                params.append(data[key])
        fields.append("updated_at = datetime('now','localtime')")
        params.append(plant_id)
        c.execute(f"UPDATE plants SET {', '.join(fields)} WHERE id = ?", params)
        if 'status' in data and data['status'] != old_status:
            change_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('''INSERT INTO plant_status_history 
                        (plant_id, old_status, new_status, change_date, notes)
                        VALUES (?, ?, ?, ?, ?)''',
                      (plant_id, old_status, data['status'], change_date, '状态变更'))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(plant_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE plants SET is_deleted = 1 WHERE id = ?", (plant_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def restore(plant_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE plants SET is_deleted = 0 WHERE id = ?", (plant_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_deleted():
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute("SELECT * FROM plants WHERE is_deleted = 1 ORDER BY updated_at DESC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_statistics():
        conn = get_conn()
        c = conn.cursor()
        total_plants = c.execute("SELECT COUNT(*) FROM plants WHERE is_deleted = 0").fetchone()[0]
        total_quantity = c.execute("SELECT COALESCE(SUM(quantity), 0) FROM plants WHERE is_deleted = 0").fetchone()[0]
        total_area = c.execute("SELECT COALESCE(SUM(area), 0) FROM plants WHERE is_deleted = 0").fetchone()[0]
        normal_count = c.execute("SELECT COUNT(*) FROM plants WHERE is_deleted = 0 AND status='正常'").fetchone()[0]
        warn_count = c.execute("SELECT COUNT(*) FROM plants WHERE is_deleted = 0 AND status='需关注'").fetchone()[0]
        sick_count = c.execute("SELECT COUNT(*) FROM plants WHERE is_deleted = 0 AND status='病虫害'").fetchone()[0]
        dead_count = c.execute("SELECT COUNT(*) FROM plants WHERE is_deleted = 0 AND status='枯死'").fetchone()[0]

        rows = c.execute("SELECT area_name, COUNT(*) as cnt, COALESCE(SUM(quantity),0) as qty "
                         "FROM plants WHERE is_deleted = 0 GROUP BY area_name").fetchall()
        by_area = [dict(row) for row in rows]

        rows = c.execute("SELECT species, COUNT(*) as cnt FROM plants "
                         "WHERE is_deleted = 0 GROUP BY species ORDER BY cnt DESC LIMIT 10").fetchall()
        by_species = [dict(row) for row in rows]

        conn.close()
        return {
            'total_plants': total_plants,
            'total_quantity': total_quantity,
            'total_area': round(total_area, 2),
            'normal_count': normal_count,
            'warn_count': warn_count,
            'sick_count': sick_count,
            'dead_count': dead_count,
            'by_area': by_area,
            'by_species': by_species
        }

    @staticmethod
    def get_areas():
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute("SELECT DISTINCT area_name FROM plants WHERE is_deleted = 0 AND area_name IS NOT NULL AND area_name != ''").fetchall()
        conn.close()
        return [row[0] for row in rows]

    @staticmethod
    def batch_delete(ids):
        conn = get_conn()
        c = conn.cursor()
        for pid in ids:
            c.execute("UPDATE plants SET is_deleted = 1 WHERE id = ?", (pid,))
        conn.commit()
        conn.close()

    @staticmethod
    def batch_update(ids, field, value):
        conn = get_conn()
        c = conn.cursor()
        for pid in ids:
            c.execute(f"UPDATE plants SET {field} = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                      (value, pid))
        conn.commit()
        conn.close()

    @staticmethod
    def get_monthly_status_by_history(plants):
        from calendar import monthrange
        monthly = {}
        now = datetime.now()
        plant_ids = [p['id'] for p in plants]
        plant_map = {p['id']: p for p in plants}

        conn = get_conn()
        c = conn.cursor()
        placeholders = ','.join('?' * len(plant_ids)) if plant_ids else '0'
        rows = c.execute(f'''SELECT plant_id, old_status, new_status, change_date
                            FROM plant_status_history
                            WHERE plant_id IN ({placeholders})
                            ORDER BY plant_id, change_date ASC''',
                         plant_ids if plant_ids else []).fetchall()
        conn.close()

        history_by_plant = {}
        for row in rows:
            pid = row['plant_id']
            if pid not in history_by_plant:
                history_by_plant[pid] = []
            history_by_plant[pid].append(dict(row))

        months = []
        for i in range(11, -1, -1):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            months.append((year, month))

        for year, month in months:
            month_key = f'{year:04d}-{month:02d}'
            _, last_day = monthrange(year, month)
            month_end = f'{year:04d}-{month:02d}-{last_day:02d} 23:59:59'

            normal = 0
            abnormal = 0
            dead = 0
            replanted = 0
            total = 0

            for p in plants:
                pid = p['id']
                created_str = p.get('created_at', '') or p.get('updated_at', '')
                if not created_str:
                    continue
                created_date = created_str[:10]
                if created_date > month_end[:10]:
                    continue

                total += 1

                if created_date[:7] == month_key:
                    replanted += 1

                status = None
                if pid in history_by_plant:
                    for h in reversed(history_by_plant[pid]):
                        h_date = h['change_date'][:10] if h['change_date'] else ''
                        if h_date and h_date <= month_end[:10]:
                            status = h['new_status']
                            break

                if status is None:
                    for h in history_by_plant.get(pid, []):
                        if h['old_status'] is None:
                            status = h['new_status']
                            break

                if status is None:
                    status = plant_map[pid].get('status', '正常')

                if status == '正常':
                    normal += 1
                elif status in ('需关注', '病虫害'):
                    abnormal += 1
                elif status == '枯死':
                    dead += 1

            monthly[month_key] = {
                'normal': normal,
                'abnormal': abnormal,
                'dead': dead,
                'replanted': replanted,
                'total': total,
            }

        return monthly


class MaintenanceManager:
    @staticmethod
    def get_plans(plant_id=None, plan_type=None):
        conn = get_conn()
        c = conn.cursor()
        query = "SELECT mp.*, p.name as plant_name FROM maintenance_plans mp " \
                "LEFT JOIN plants p ON mp.plant_id = p.id WHERE mp.is_deleted = 0"
        params = []
        if plant_id:
            query += " AND mp.plant_id = ?"
            params.append(plant_id)
        if plan_type:
            query += " AND mp.plan_type = ?"
            params.append(plan_type)
        query += " ORDER BY mp.next_date ASC"
        rows = c.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def add_plan(data):
        conn = get_conn()
        c = conn.cursor()
        c.execute('''INSERT INTO maintenance_plans 
                    (plant_id, plan_type, frequency_days, last_date, next_date, responsible, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (data.get('plant_id'), data.get('plan_type'),
                   data.get('frequency_days', 7), data.get('last_date'),
                   data.get('next_date'), data.get('responsible'), data.get('notes')))
        plan_id = c.lastrowid
        conn.commit()
        conn.close()
        return plan_id

    @staticmethod
    def update_plan(plan_id, data):
        conn = get_conn()
        c = conn.cursor()
        fields = []
        params = []
        for key in ['plant_id', 'plan_type', 'frequency_days', 'last_date',
                    'next_date', 'responsible', 'notes']:
            if key in data:
                fields.append(f"{key} = ?")
                params.append(data[key])
        params.append(plan_id)
        c.execute(f"UPDATE maintenance_plans SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    @staticmethod
    def delete_plan(plan_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE maintenance_plans SET is_deleted = 1 WHERE id = ?", (plan_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_today_tasks():
        conn = get_conn()
        c = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        rows = c.execute('''SELECT mp.*, p.name as plant_name, p.area_name, p.species
                            FROM maintenance_plans mp
                            LEFT JOIN plants p ON mp.plant_id = p.id
                            WHERE mp.is_deleted = 0 AND mp.next_date <= ?
                            ORDER BY mp.next_date ASC''', (today,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_week_tasks():
        conn = get_conn()
        c = conn.cursor()
        today = datetime.now()
        week_end = (today + timedelta(days=7)).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        rows = c.execute('''SELECT mp.*, p.name as plant_name, p.area_name, p.species
                            FROM maintenance_plans mp
                            LEFT JOIN plants p ON mp.plant_id = p.id
                            WHERE mp.is_deleted = 0 AND mp.next_date <= ? AND mp.next_date >= ?
                            ORDER BY mp.next_date ASC''', (week_end, today_str)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def complete_task(plan_id):
        conn = get_conn()
        c = conn.cursor()
        plan = c.execute("SELECT * FROM maintenance_plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan:
            conn.close()
            return
        today = datetime.now().strftime('%Y-%m-%d')
        next_date = (datetime.now() + timedelta(days=plan['frequency_days'])).strftime('%Y-%m-%d')
        c.execute("UPDATE maintenance_plans SET last_date = ?, next_date = ? WHERE id = ?",
                  (today, next_date, plan_id))
        c.execute('''INSERT INTO maintenance_records (plan_id, plant_id, record_type, record_date, operator, result)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                  (plan_id, plan['plant_id'], plan['plan_type'], today, plan['responsible'], '已完成'))
        conn.commit()
        conn.close()

    @staticmethod
    def get_records(plant_id=None, limit=50):
        conn = get_conn()
        c = conn.cursor()
        query = "SELECT mr.*, p.name as plant_name FROM maintenance_records mr " \
                "LEFT JOIN plants p ON mr.plant_id = p.id WHERE 1=1"
        params = []
        if plant_id:
            query += " AND mr.plant_id = ?"
            params.append(plant_id)
        query += " ORDER BY mr.record_date DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_monthly_survival_rate():
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute('''SELECT 
                            strftime('%Y-%m', mr.record_date) as month,
                            COUNT(*) as total,
                            SUM(CASE WHEN mr.result = '已完成' THEN 1 ELSE 0 END) as completed
                            FROM maintenance_records mr
                            WHERE mr.record_date >= date('now', '-12 months')
                            GROUP BY month
                            ORDER BY month ASC''').fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_plan(plan_id):
        conn = get_conn()
        c = conn.cursor()
        row = c.execute('''SELECT mp.*, p.name as plant_name, p.area_name
                            FROM maintenance_plans mp
                            LEFT JOIN plants p ON mp.plant_id = p.id
                            WHERE mp.id = ? AND mp.is_deleted = 0''', (plan_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_plan_date(plan_id, new_date):
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE maintenance_plans SET next_date = ? WHERE id = ?",
                  (new_date, plan_id))
        conn.commit()
        conn.close()

    @staticmethod
    def get_all_tasks_within_range(start_date, end_date):
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute('''SELECT mp.*, p.name as plant_name, p.area_name, p.species
                            FROM maintenance_plans mp
                            LEFT JOIN plants p ON mp.plant_id = p.id
                            WHERE mp.is_deleted = 0 
                              AND mp.next_date >= ? 
                              AND mp.next_date <= ?
                            ORDER BY mp.next_date ASC''', (start_date, end_date)).fetchall()
        conn.close()
        return [dict(row) for row in rows]


class PhotoManager:
    @staticmethod
    def get_all(plant_id=None, month=None, plant_status=None):
        conn = get_conn()
        c = conn.cursor()
        query = "SELECT ph.*, p.name as plant_name, p.status as plant_status FROM photos ph " \
                "LEFT JOIN plants p ON ph.plant_id = p.id WHERE 1=1"
        params = []
        if plant_id:
            query += " AND ph.plant_id = ?"
            params.append(plant_id)
        if month:
            query += " AND strftime('%Y-%m', COALESCE(ph.shot_date, ph.upload_date)) = ?"
            params.append(month)
        if plant_status and plant_status != '全部状态':
            query += " AND (p.status = ? OR ph.abnormal_status = ?)"
            params.extend([plant_status, plant_status])
        query += " ORDER BY COALESCE(ph.shot_date, ph.upload_date) DESC"
        rows = c.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def add(plant_id, file_path, shot_date=None, description='', abnormal_status='无异常'):
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO photos (plant_id, file_path, shot_date, description, abnormal_status) VALUES (?, ?, ?, ?, ?)",
                  (plant_id, file_path, shot_date, description, abnormal_status))
        photo_id = c.lastrowid
        conn.commit()
        conn.close()
        return photo_id

    @staticmethod
    def get_available_months():
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute('''SELECT DISTINCT strftime('%Y-%m', COALESCE(shot_date, upload_date)) as month
                            FROM photos ORDER BY month DESC''').fetchall()
        conn.close()
        return [row['month'] for row in rows if row['month']]

    @staticmethod
    def get_photos_with_timeline(plant_id, month=None, plant_status=None):
        conn = get_conn()
        c = conn.cursor()
        query = '''SELECT ph.*, p.name as plant_name, p.status as plant_status
                    FROM photos ph
                    LEFT JOIN plants p ON ph.plant_id = p.id
                    WHERE ph.plant_id = ?'''
        params = [plant_id]
        if month:
            query += " AND strftime('%Y-%m', COALESCE(ph.shot_date, ph.upload_date)) = ?"
            params.append(month)
        if plant_status and plant_status != '全部状态':
            query += " AND (p.status = ? OR ph.abnormal_status = ?)"
            params.extend([plant_status, plant_status])
        query += " ORDER BY COALESCE(ph.shot_date, ph.upload_date) DESC"
        rows = c.execute(query, params).fetchall()
        conn.close()
        photos = [dict(row) for row in rows]

        photos_by_month = {}
        for photo in photos:
            date_str = photo.get('shot_date') or photo.get('upload_date') or ''
            if len(date_str) >= 7:
                month = date_str[:7]
                if month not in photos_by_month:
                    photos_by_month[month] = []
                photos_by_month[month].append(photo)
        return photos_by_month

    @staticmethod
    def delete(photo_id):
        conn = get_conn()
        c = conn.cursor()
        photo = c.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
        if photo and os.path.exists(photo['file_path']):
            try:
                os.remove(photo['file_path'])
            except:
                pass
        c.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
        conn.close()


class ExpenseManager:
    @staticmethod
    def get_all(expense_type=None, year=None):
        conn = get_conn()
        c = conn.cursor()
        query = "SELECT e.*, p.name as plant_name FROM expenses e " \
                "LEFT JOIN plants p ON e.related_plant_id = p.id WHERE 1=1"
        params = []
        if expense_type:
            query += " AND e.expense_type = ?"
            params.append(expense_type)
        if year:
            query += " AND strftime('%Y', e.expense_date) = ?"
            params.append(str(year))
        query += " ORDER BY e.expense_date DESC"
        rows = c.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def add(data):
        conn = get_conn()
        c = conn.cursor()
        c.execute('''INSERT INTO expenses 
                    (expense_type, amount, expense_date, vendor, contract_end_date, related_plant_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (data.get('expense_type'), data.get('amount'),
                   data.get('expense_date'), data.get('vendor'),
                   data.get('contract_end_date'), data.get('related_plant_id'),
                   data.get('notes')))
        expense_id = c.lastrowid
        conn.commit()
        conn.close()
        return expense_id

    @staticmethod
    def update(expense_id, data):
        conn = get_conn()
        c = conn.cursor()
        fields = []
        params = []
        for key in ['expense_type', 'amount', 'expense_date', 'vendor',
                    'contract_end_date', 'related_plant_id', 'notes']:
            if key in data:
                fields.append(f"{key} = ?")
                params.append(data[key])
        params.append(expense_id)
        c.execute(f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    @staticmethod
    def delete(expense_id):
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_contracts_soon(days=30):
        conn = get_conn()
        c = conn.cursor()
        target_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        rows = c.execute('''SELECT * FROM expenses 
                            WHERE contract_end_date IS NOT NULL 
                            AND contract_end_date != ''
                            AND contract_end_date <= ?
                            AND contract_end_date >= ?
                            ORDER BY contract_end_date ASC''',
                         (target_date, today)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_monthly_expenses():
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute('''SELECT
                            strftime('%Y-%m', expense_date) as month,
                            expense_type,
                            COALESCE(SUM(amount), 0) as total
                            FROM expenses
                            WHERE expense_date >= date('now', '-12 months')
                            GROUP BY month, expense_type
                            ORDER BY month ASC''').fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_monthly_expenses_by_type(area_name=None):
        conn = get_conn()
        c = conn.cursor()
        query = '''SELECT
                    strftime('%Y-%m', e.expense_date) as month,
                    e.expense_type,
                    COALESCE(SUM(e.amount), 0) as total
                    FROM expenses e
                    LEFT JOIN plants p ON e.related_plant_id = p.id
                    WHERE 1=1'''
        params = []
        if area_name:
            query += ' AND p.area_name = ?'
            params.append(area_name)
        query += ' GROUP BY month, e.expense_type ORDER BY month ASC'
        rows = c.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_total_expense():
        conn = get_conn()
        c = conn.cursor()
        total = c.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses").fetchone()[0]
        conn.close()
        return round(total, 2)

    @staticmethod
    def set_budget(year, category, area_name, amount, notes=''):
        conn = get_conn()
        c = conn.cursor()
        c.execute('''DELETE FROM budgets WHERE year = ? AND category = ? AND COALESCE(area_name, '') = COALESCE(?, '')''',
                  (year, category, area_name))
        c.execute('''INSERT INTO budgets (year, category, area_name, budget_amount, notes)
                    VALUES (?, ?, ?, ?, ?)''',
                  (year, category, area_name if area_name else None, amount, notes))
        conn.commit()
        conn.close()

    @staticmethod
    def get_budgets(year=None):
        conn = get_conn()
        c = conn.cursor()
        query = "SELECT * FROM budgets WHERE 1=1"
        params = []
        if year:
            query += " AND year = ?"
            params.append(year)
        query += " ORDER BY year DESC, category, area_name"
        rows = c.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_budget_progress(year, category=None, area_name=None):
        conn = get_conn()
        c = conn.cursor()
        query = "SELECT * FROM budgets WHERE year = ?"
        params = [year]
        if category:
            query += " AND category = ?"
            params.append(category)
        if area_name:
            query += " AND COALESCE(area_name, '') = COALESCE(?, '')"
            params.append(area_name)
        rows = c.execute(query, params).fetchall()

        result = []
        for row in rows:
            b = dict(row)
            spent = 0.0
            if b['area_name']:
                spent_row = c.execute(
                    '''SELECT COALESCE(SUM(e.amount), 0) FROM expenses e
                       LEFT JOIN plants p ON e.related_plant_id = p.id
                       WHERE e.expense_type = ? AND p.area_name = ? AND strftime('%Y', e.expense_date) = ?''',
                    (b['category'], b['area_name'], str(year))
                ).fetchone()
                spent = spent_row[0] if spent_row else 0.0
            else:
                spent_row = c.execute(
                    '''SELECT COALESCE(SUM(amount), 0) FROM expenses
                       WHERE expense_type = ? AND strftime('%Y', expense_date) = ?''',
                    (b['category'], str(year))
                ).fetchone()
                spent = spent_row[0] if spent_row else 0.0

            budget_amount = b['budget_amount']
            progress_pct = round(spent / budget_amount * 100, 1) if budget_amount > 0 else 0
            result.append({
                'category': b['category'],
                'area_name': b['area_name'] or '',
                'budget_amount': budget_amount,
                'spent_amount': round(spent, 2),
                'progress_pct': progress_pct,
            })
        conn.close()
        return result


class SettingsManager:
    @staticmethod
    def get(key, default=None):
        conn = get_conn()
        c = conn.cursor()
        row = c.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row['value'] if row else default

    @staticmethod
    def set(key, value):
        conn = get_conn()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''',
                  (key, str(value)))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(key):
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        conn.close()


class BackupManager:
    @staticmethod
    def create_backup(description=''):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUP_DIR, f'backup_{timestamp}.db')
        shutil.copy2(DB_PATH, backup_file)

        conn = get_conn()
        c = conn.cursor()
        count = c.execute("SELECT COUNT(*) FROM plants WHERE is_deleted = 0").fetchone()[0]
        c.execute("INSERT INTO backup_records (file_path, description, record_count) VALUES (?, ?, ?)",
                  (backup_file, description, count))
        conn.commit()
        conn.close()
        return backup_file

    @staticmethod
    def get_backups():
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute("SELECT * FROM backup_records ORDER BY backup_date DESC").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def restore_backup(backup_file):
        if not os.path.exists(backup_file):
            return False
        try:
            current_backup = BackupManager.create_backup('恢复前自动备份')
        except:
            pass
        shutil.copy2(backup_file, DB_PATH)
        return True

    @staticmethod
    def delete_backup(backup_id):
        conn = get_conn()
        c = conn.cursor()
        record = c.execute("SELECT * FROM backup_records WHERE id = ?", (backup_id,)).fetchone()
        if record and os.path.exists(record['file_path']):
            try:
                os.remove(record['file_path'])
            except:
                pass
        c.execute("DELETE FROM backup_records WHERE id = ?", (backup_id,))
        conn.commit()
        conn.close()
