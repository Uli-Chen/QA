import csv

# 输入输出文件路径（可以根据需要修改）
input_file = './data/teams.csv'
output_file = './data/teams_cleaned.csv'

# 打开输入文件并处理
with open(input_file, mode='r', encoding='utf-8', newline='') as infile, \
     open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
    
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames  # 获取标题行
    
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()  # 写入标题行

    for row in reader:
        if row['year'] == '2024':  
            writer.writerow(row)

