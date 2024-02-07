all: paper.pdf revisionreport.pdf

paper.pdf: \
		paper.tex \
		abstract.tex \
		bg.tex \
		eval.tex \
		intro.tex \
		related.tex \
		summ.tex \
		system.tex \
		threats.tex \
		ack.tex \
		duncan.tex \
		chen.tex 
	pdflatex paper
	bibtex paper
	pdflatex paper
	pdflatex paper

revisionreport.pdf: \
		revisionreport.tex revisionreport_content.tex
	pdflatex revisionreport
	bibtex revisionreport
	pdflatex revisionreport
	pdflatex revisionreport
	


clean:
	$(RM) *.aux *.log *.spl *.bbl
