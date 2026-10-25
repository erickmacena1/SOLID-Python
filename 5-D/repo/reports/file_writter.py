class ReportFileWritter():

    @staticmethod
    def write_file(report):
        file = open('report.txt', 'w')
        file.write(report)
        file.close()