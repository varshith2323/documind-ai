from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

output_file = "sample_handbook.pdf"

document = SimpleDocTemplate(
    output_file,
    pagesize=A4,
)

styles = getSampleStyleSheet()
story = []

with open("sample_handbook.txt", "r", encoding="utf-8") as file:
    for line in file:
        line = line.strip()

        if line:
            story.append(Paragraph(line, styles["Normal"]))
            story.append(Spacer(1, 8))

document.build(story)

print(f"Created {output_file}")