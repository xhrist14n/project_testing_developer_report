import os
import sys
import datetime
from github import Github
import pandas as pd

# Parámetros de entorno
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPORT_DATE_START = os.getenv("REPORT_DATE_START")
REPORT_DATE_END = os.getenv("REPORT_DATE_END")
REPO_NAME = os.getenv("GITHUB_REPOSITORY", "xhrist14n/project_testing_developer_report")

# Fechas
try:
    date_start = datetime.datetime.strptime(REPORT_DATE_START, "%d/%m/%Y")
    date_end = datetime.datetime.strptime(REPORT_DATE_END, "%d/%m/%Y")
except Exception:
    print("Fechas inválidas. Formato esperado: dd/MM/yyyy")
    sys.exit(1)

# Conexión a GitHub
if not GITHUB_TOKEN:
    print("Falta GITHUB_TOKEN")
    sys.exit(1)
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# Recolectar PRs en el rango de fechas
pulls = repo.get_pulls(state='all', sort='updated', direction='desc')
pr_data = []
for pr in pulls:
    pr_created = pr.created_at.replace(tzinfo=None)
    if pr_created < date_start or pr_created > date_end:
        continue
    # Buscar errores de CI (checks fallidos)
    sha = pr.head.sha
    try:
        commit = repo.get_commit(sha)
        checks = commit.get_check_runs()
        failed_checks = [c for c in checks if c.conclusion == 'failure']
    except Exception:
        failed_checks = []
    pr_data.append({
        'PR': pr.number,
        'Autor': pr.user.login,
        'Fecha': pr_created.strftime('%Y-%m-%d'),
        'Errores_CI': len(failed_checks),
        'Titulo': pr.title,
        'URL': pr.html_url
    })

# Convertir a DataFrame
if pr_data:
    df = pd.DataFrame(pr_data)
else:
    df = pd.DataFrame(columns=['PR','Autor','Fecha','Errores_CI','Titulo','URL'])

# Guardar Excel
df.to_excel('error_report.xlsx', index=False)

# Generar Markdown
with open('error_report.md', 'w', encoding='utf-8') as f:
    f.write(f"# Reporte de Errores en Pull Requests\n\n")
    f.write(f"Periodo: {REPORT_DATE_START} a {REPORT_DATE_END}\n\n")
    f.write(f"## Tabla de Errores por PR\n\n")
    if df.empty:
        f.write('No se encontraron PRs en el rango de fechas.\n')
    else:
        f.write('| PR | Autor | Fecha | Errores CI | Título |\n')
        f.write('|----|-------|-------|------------|--------|\n')
        for _, row in df.iterrows():
            f.write(f"| [{int(row['PR'])}]({row['URL']}) | {row['Autor']} | {row['Fecha']} | {row['Errores_CI']} | {row['Titulo']} |\n")
    f.write('\n')
    # Gráfica Mermaid: Errores en el tiempo
    f.write('## Gráfica de Errores en el Tiempo (Mermaid)\n')
    f.write('```mermaid\ngantt\n    dateFormat  YYYY-MM-DD\n    axisFormat  %d/%m\n')
    for _, row in df.iterrows():
        if row['Errores_CI'] > 0:
            f.write(f"    section {row['Autor']}\n    PR#{int(row['PR'])} :done, {row['Fecha']}, 1d\n")
    f.write('\n\n')
    # Predicción simple (tendencia lineal)
    f.write('## Predicción de Errores Futuros\n')
    if not df.empty:
        errores_por_fecha = df.groupby('Fecha')['Errores_CI'].sum().reset_index()
        f.write('```mermaid\nline\n')
        f.write('    title Errores de CI por día\n')
        f.write('    x-axis Fecha\n    y-axis Errores\n')
        for _, row in errores_por_fecha.iterrows():
            f.write(f"    {row['Fecha']} : {row['Errores_CI']}\n")
        f.write("")
    else:
        f.write('No hay datos suficientes para predicción.\n')

print("Reporte generado: error_report.md y error_report.xlsx")
