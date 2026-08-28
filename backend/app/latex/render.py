"""Deterministic LaTeX rendering of a Tailored Resume (ADR-0001).

The renderer owns all layout: section order, margins, typography, spacing,
bullets, and hyperlinks. Content is escaped through LatexEscapeService; the
LLM never influences structure.
"""

from app.domain.resume import (
    Certification,
    Education,
    Experience,
    MonthYear,
    PersonalInformation,
    Project,
)
from app.domain.tailoring import TailoredResume
from app.latex.escape import LatexEscapeService

PREAMBLE = r"""\documentclass[10pt]{article}
\usepackage[letterpaper,margin=0.7in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\IfFileExists{enumitem.sty}{\usepackage{enumitem}}{}
\IfFileExists{titlesec.sty}{\usepackage{titlesec}}{}
\usepackage[hidelinks]{hyperref}
\input glyphtounicode
\pdfgentounicode=1
\pagestyle{empty}
\setlength{\parindent}{0pt}
\makeatletter
\IfFileExists{titlesec.sty}{%
  \titleformat{\section}{\large\bfseries\scshape}{}{0em}{}[\titlerule]%
  \titlespacing*{\section}{0pt}{10pt}{4pt}%
}{%
  \renewcommand{\section}{\@startsection{section}{1}{\z@}{10pt}{4pt}{\normalfont\large\bfseries\scshape}}%
}
\makeatother
\IfFileExists{enumitem.sty}{%
  \setlist[itemize]{leftmargin=1.1em,itemsep=1pt,topsep=2pt,parsep=0pt}%
}{%
  \setlength{\parskip}{0pt}%
}
\begin{document}"""


class LatexRenderingService:
    """Renders a Tailored Resume to deterministic ``.tex`` source.

    The template owns the section order (Summary, Skills, Experience,
    Projects, Education, Certifications after the contact header), margins,
    typography, spacing, bullets, and hyperlinks. Identical input yields
    identical output.
    """

    def __init__(self, escape: LatexEscapeService | None = None) -> None:
        self._escape = escape or LatexEscapeService()

    def render(self, tailored: TailoredResume) -> str:
        parts = [PREAMBLE]
        parts.append(self._header(tailored))
        if tailored.summary:
            parts.append(self._section("Summary", self._escape.escape(tailored.summary)))
        if tailored.skills:
            parts.append(self._section("Skills", self._skills(tailored.skills)))
        if tailored.experience:
            parts.append(self._section("Experience", self._experience(tailored.experience)))
        if tailored.projects:
            parts.append(self._section("Projects", self._projects(tailored.projects)))
        if tailored.education:
            parts.append(self._section("Education", self._education(tailored.education)))
        if tailored.certifications:
            parts.append(
                self._section("Certifications", self._certifications(tailored.certifications))
            )
        parts.append(r"\end{document}")
        return "\n".join(parts)

    def _header(self, tailored: TailoredResume) -> str:
        info = tailored.personal_information
        lines = [r"\begin{center}"]
        lines.append(r"{\LARGE\bfseries " + self._escape.escape(info.full_name) + "}")
        if info.headline:
            lines.append(r"{\large\scshape " + self._escape.escape(info.headline) + "}")
        contact = self._contact(info)
        if contact:
            lines.append(contact)
        lines.append(r"\end{center}")
        return "\n".join(lines)

    def _contact(self, info: PersonalInformation) -> str:
        items = []
        if info.email:
            items.append(self._escape.escape(info.email))
        if info.phone:
            items.append(self._escape.escape(info.phone))
        if info.location:
            items.append(self._escape.escape(info.location))
        if info.website:
            items.append(self._href(info.website, info.website))
        return " $|$ ".join(items)

    def _section(self, title: str, body: str) -> str:
        return f"\\section*{{{title}}}\n{body}"

    @staticmethod
    def _bold(text: str) -> str:
        return rf"\textbf{{{text}}}"

    @staticmethod
    def _italic(text: str) -> str:
        return rf"\textit{{{text}}}"

    def _skills(self, skills: dict[str, list[str]]) -> str:
        lines = []
        for category, names in skills.items():
            names_text = ", ".join(self._escape.escape(name) for name in names)
            lines.append(self._bold(self._escape.escape(category)) + " " + names_text)
        return "\\\\\n".join(lines)

    def _experience(self, experience: list[Experience]) -> str:
        return "\n\n".join(self._experience_block(exp) for exp in experience)

    def _experience_block(self, exp: Experience) -> str:
        lines = []
        title_line = self._bold(self._escape.escape(exp.title))
        title_line += r"\hfill " + self._date_range(exp.start_date, exp.end_date)
        lines.append(title_line)
        employer = ", ".join(part for part in (exp.company, exp.location) if part)
        if employer:
            lines.append(self._italic(self._escape.escape(employer)))
        if exp.summary:
            lines.append(self._escape.escape(exp.summary))
        if exp.bullets:
            lines.append(self._bullets(exp.bullets))
        return "\n".join(lines)

    def _projects(self, projects: list[Project]) -> str:
        return "\n\n".join(self._project_block(proj) for proj in projects)

    def _project_block(self, proj: Project) -> str:
        lines = []
        name_line = self._bold(self._escape.escape(proj.name))
        if proj.url:
            name_line += r"\hfill " + self._href(proj.url, proj.url)
        lines.append(name_line)
        if proj.description:
            lines.append(self._escape.escape(proj.description))
        if proj.bullets:
            lines.append(self._bullets(proj.bullets))
        return "\n".join(lines)

    def _education(self, education: list[Education]) -> str:
        return "\n\n".join(self._education_block(edu) for edu in education)

    def _education_block(self, edu: Education) -> str:
        lines = []
        if edu.degree or edu.field:
            label = ", ".join(part for part in (edu.degree, edu.field) if part)
        else:
            label = edu.school
        line = self._bold(self._escape.escape(label))
        line += r"\hfill " + self._date_range(edu.start_date, edu.end_date)
        lines.append(line)
        if edu.degree or edu.field:
            school = ", ".join(part for part in (edu.school, edu.location) if part)
            if school:
                lines.append(self._italic(self._escape.escape(school)))
        return "\n".join(lines)

    def _certifications(self, certifications: list[Certification]) -> str:
        blocks = []
        for cert in certifications:
            lines = []
            line = self._bold(self._escape.escape(cert.name))
            line += r"\hfill " + cert.date.render()
            lines.append(line)
            right = self._escape.escape(cert.issuer) if cert.issuer else ""
            if cert.url:
                right += r"\hfill " + self._href(cert.url, cert.url)
            lines.append(self._italic(right))
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def _bullets(self, bullets: list[str]) -> str:
        items = "\n".join(r"\item " + self._escape.escape(bullet) for bullet in bullets)
        return r"\begin{itemize}" + "\n" + items + "\n" + r"\end{itemize}"

    @staticmethod
    def _date_range(start: MonthYear, end: MonthYear | None) -> str:
        end_text = end.render() if end is not None else "Present"
        return f"{start.render()} -- {end_text}"

    def _href(self, url: str, label: str) -> str:
        escaped_url = self._escape.escape_url(url)
        return rf"\href{{{escaped_url}}}{{{self._escape.escape(label)}}}"