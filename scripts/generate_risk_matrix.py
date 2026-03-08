import json
from datetime import datetime

severity_order = {
    'CRITICAL': 0,
    'HIGH': 1,
    'MEDIUM': 2,
    'LOW': 3,
    'INFO': 4
}

def generate():
    with open('reports/phase3/classified-vulnerabilities.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    vulnerabilities = data.get('vulnerabilities', [])
    
    # Sort by severity
    vulnerabilities.sort(key=lambda x: severity_order.get(x.get('severity', 'INFO'), 5))
    
    risk_matrix_data = []
    for v in vulnerabilities:
        cia = v.get('cia_impact', {})
        impact_str = f"C: {cia.get('confidentiality', 'N/A')}, I: {cia.get('integrity', 'N/A')}, A: {cia.get('availability', 'N/A')}"
        
        risk_matrix_data.append({
            'id': v.get('id'),
            'vulnerability': v.get('title'),
            'category': v.get('domain'),
            'severity': v.get('severity'),
            'impact': impact_str,
            'recommendation': v.get('remediation')
        })
        
    # Write JSON
    output_json = {
        'meta': {
            'version': '1.0.0',
            'project': 'ESAA Security Audit',
            'phase': 'Phase 3 - Risk Matrix',
            'total_vulnerabilities': len(risk_matrix_data),
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        },
        'risk_matrix': risk_matrix_data
    }
    
    with open('reports/phase3/risk-matrix.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)
        
    # Write MD
    with open('reports/phase3/risk-matrix.md', 'w', encoding='utf-8') as f:
        f.write('# Matriz de Riscos Consolidada\n\n')
        f.write('Este documento apresenta a matriz consolidada de vulnerabilidades identificadas durante a auditoria de segurança do sistema ESAA, categorizadas por domínio e ordenadas por severidade decrescente.\n\n')
        f.write('| ID | Vulnerabilidade | Categoria | Severidade | Impacto (CIA) | Recomendação |\n')
        f.write('|:---|:----------------|:----------|:-----------|:--------------|:-------------|\n')
        for r in risk_matrix_data:
            severity = r['severity']
            if severity in ['CRITICAL', 'HIGH']:
                severity_md = f'**{severity}**'
            else:
                severity_md = severity
                
            f.write(f"| {r['id']} | {r['vulnerability']} | {r['category']} | {severity_md} | {r['impact']} | {r['recommendation']} |\n")

if __name__ == "__main__":
    generate()
