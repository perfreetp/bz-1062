import os
from datetime import datetime, timedelta
from database import init_db, PlantManager, MaintenanceManager, ExpenseManager, get_conn

SAMPLE_PLANTS = [
    {'name': '香樟树', 'species': '樟科樟属', 'spec': '胸径15-18cm', 'quantity': 12, 'area': 45.6,
     'position_x': 0.15, 'position_y': 0.25, 'area_name': '东门广场', 'responsible': '张师傅',
     'status': '正常', 'plant_date': '2022-03-15', 'notes': '行道树，生长良好'},
    {'name': '桂花树', 'species': '木犀科木犀属', 'spec': '高3-4m', 'quantity': 8, 'area': 24.0,
     'position_x': 0.32, 'position_y': 0.18, 'area_name': '办公楼前', 'responsible': '李师傅',
     'status': '正常', 'plant_date': '2021-09-20', 'notes': '秋季开花，香气宜人'},
    {'name': '广玉兰', 'species': '木兰科木兰属', 'spec': '胸径20cm', 'quantity': 5, 'area': 35.0,
     'position_x': 0.55, 'position_y': 0.32, 'area_name': '中心花园', 'responsible': '王师傅',
     'status': '需关注', 'plant_date': '2020-05-10', 'notes': '部分叶片发黄，需检查'},
    {'name': '樱花树', 'species': '蔷薇科樱属', 'spec': '地径12cm', 'quantity': 15, 'area': 52.5,
     'position_x': 0.72, 'position_y': 0.22, 'area_name': '樱花大道', 'responsible': '张师傅',
     'status': '正常', 'plant_date': '2023-02-28', 'notes': '春季观花，已建樱花林'},
    {'name': '紫薇', 'species': '千屈菜科紫薇属', 'spec': '地径8cm', 'quantity': 20, 'area': 30.0,
     'position_x': 0.25, 'position_y': 0.55, 'area_name': '南门绿化带', 'responsible': '赵师傅',
     'status': '正常', 'plant_date': '2022-06-10', 'notes': '夏季开花，花期长'},
    {'name': '红叶石楠', 'species': '蔷薇科石楠属', 'spec': '高1.5m球', 'quantity': 50, 'area': 25.0,
     'position_x': 0.45, 'position_y': 0.62, 'area_name': '中心花园', 'responsible': '李师傅',
     'status': '正常', 'plant_date': '2023-04-05', 'notes': '绿篱植物，新叶红色'},
    {'name': '金森女贞', 'species': '木犀科女贞属', 'spec': '高1.2m球', 'quantity': 80, 'area': 40.0,
     'position_x': 0.65, 'position_y': 0.58, 'area_name': '停车场周边', 'responsible': '王师傅',
     'status': '病虫害', 'plant_date': '2021-07-15', 'notes': '发现蚜虫，需打药防治'},
    {'name': '海桐', 'species': '海桐科海桐属', 'spec': '高1.5m球', 'quantity': 30, 'area': 22.5,
     'position_x': 0.82, 'position_y': 0.45, 'area_name': '西门入口', 'responsible': '赵师傅',
     'status': '正常', 'plant_date': '2022-01-20', 'notes': '四季常青，耐修剪'},
    {'name': '红花檵木', 'species': '金缕梅科檵木属', 'spec': '高1m球', 'quantity': 60, 'area': 18.0,
     'position_x': 0.12, 'position_y': 0.72, 'area_name': '北门花坛', 'responsible': '张师傅',
     'status': '正常', 'plant_date': '2023-03-12', 'notes': '观叶观花植物'},
    {'name': '马尼拉草皮', 'species': '禾本科结缕草属', 'spec': '满铺', 'quantity': 1, 'area': 850.0,
     'position_x': 0.42, 'position_y': 0.42, 'area_name': '中心草坪', 'responsible': '李师傅',
     'status': '正常', 'plant_date': '2020-08-01', 'notes': '主要草坪区域，定期修剪'},
    {'name': '麦冬草', 'species': '百合科沿阶草属', 'spec': '地被', 'quantity': 1, 'area': 120.0,
     'position_x': 0.85, 'position_y': 0.75, 'area_name': '道路边', 'responsible': '王师傅',
     'status': '枯死', 'plant_date': '2021-05-20', 'notes': '部分区域枯死，需补植'},
    {'name': '茶花', 'species': '山茶科山茶属', 'spec': '冠幅1.2m', 'quantity': 10, 'area': 15.0,
     'position_x': 0.58, 'position_y': 0.78, 'area_name': '茶花园区', 'responsible': '赵师傅',
     'status': '正常', 'plant_date': '2022-11-08', 'notes': '冬春开花，品种多样'},
]

SAMPLE_PLANS = [
    {'plant_idx': 0, 'plan_type': '浇水', 'frequency_days': 5, 'offset_days': 2},
    {'plant_idx': 0, 'plan_type': '施肥', 'frequency_days': 30, 'offset_days': 5},
    {'plant_idx': 1, 'plan_type': '浇水', 'frequency_days': 7, 'offset_days': 1},
    {'plant_idx': 2, 'plan_type': '浇水', 'frequency_days': 4, 'offset_days': 0},
    {'plant_idx': 3, 'plan_type': '浇水', 'frequency_days': 6, 'offset_days': 3},
    {'plant_idx': 4, 'plan_type': '修剪', 'frequency_days': 60, 'offset_days': 10},
    {'plant_idx': 6, 'plan_type': '打药', 'frequency_days': 15, 'offset_days': 1},
    {'plant_idx': 9, 'plan_type': '修剪', 'frequency_days': 20, 'offset_days': 2},
    {'plant_idx': 9, 'plan_type': '浇水', 'frequency_days': 10, 'offset_days': 1},
    {'plant_idx': 5, 'plan_type': '修剪', 'frequency_days': 45, 'offset_days': 5},
]

SAMPLE_EXPENSES = [
    {'expense_type': '采购', 'amount': 15800.00, 'expense_date': '2026-01-15', 'vendor': '绿源苗木基地',
     'contract_end_date': '2026-12-31', 'notes': '2026年度苗木采购合同'},
    {'expense_type': '养护', 'amount': 36000.00, 'expense_date': '2026-03-01', 'vendor': '丽景园林养护公司',
     'contract_end_date': '2026-12-15', 'notes': '年度绿化养护服务'},
    {'expense_type': '肥料', 'amount': 3500.00, 'expense_date': '2026-04-10', 'vendor': '丰收农资',
     'contract_end_date': '', 'notes': '复合肥50袋'},
    {'expense_type': '农药', 'amount': 1200.00, 'expense_date': '2026-05-20', 'vendor': '绿保植保',
     'contract_end_date': '', 'notes': '杀虫剂、杀菌剂一批'},
    {'expense_type': '补植', 'amount': 2800.00, 'expense_date': '2026-02-28', 'vendor': '绿源苗木基地',
     'contract_end_date': '', 'notes': '麦冬草补植20㎡'},
    {'expense_type': '设备', 'amount': 8500.00, 'expense_date': '2026-03-15', 'vendor': '园林机械专营店',
     'contract_end_date': '2027-03-14', 'notes': '草坪修剪机2台，质保一年'},
    {'expense_type': '其他', 'amount': 500.00, 'expense_date': '2026-06-01', 'vendor': '',
     'contract_end_date': '', 'notes': '工具耗材'},
]


def generate_sample_data():
    init_db()

    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM plants WHERE is_deleted = 0").fetchone()[0]
    conn.close()

    if count > 0:
        print(f'数据库中已有 {count} 条植株记录，跳过示例数据生成')
        return False

    print('正在生成示例数据...')

    plant_ids = []
    for p in SAMPLE_PLANTS:
        pid = PlantManager.add(p)
        plant_ids.append(pid)

    today = datetime.now()
    for plan_info in SAMPLE_PLANS:
        plant_id = plant_ids[plan_info['plant_idx']]
        last_date = (today - timedelta(days=plan_info['offset_days'])).strftime('%Y-%m-%d')
        next_date = (today + timedelta(days=plan_info['frequency_days'] - plan_info['offset_days'])).strftime('%Y-%m-%d')

        plant = PlantManager.get_by_id(plant_id)
        data = {
            'plant_id': plant_id,
            'plan_type': plan_info['plan_type'],
            'frequency_days': plan_info['frequency_days'],
            'last_date': last_date,
            'next_date': next_date,
            'responsible': plant.get('responsible', ''),
            'notes': '',
        }
        MaintenanceManager.add_plan(data)

    for e in SAMPLE_EXPENSES:
        ExpenseManager.add(e)

    print(f'示例数据生成完成：')
    print(f'  - 植株记录：{len(SAMPLE_PLANTS)} 条')
    print(f'  - 养护计划：{len(SAMPLE_PLANS)} 条')
    print(f'  - 费用记录：{len(SAMPLE_EXPENSES)} 条')
    return True


if __name__ == '__main__':
    generate_sample_data()
