from .file_writter import ReportFileWritter

class ReportWritter():

    @staticmethod
    def write(report, writter=ReportFileWritter):
        # lógica...
        # lógica...
        # report = faz_alguma_coisa
        writter.write(report)