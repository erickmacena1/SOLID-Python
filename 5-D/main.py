from github.client import GithubClient
from repo.parser import RepoParser
from repo.reports_generator import ReportsGenerator
from repo.reports.markdown_generator import MarkdownGenerator
from repo.reports.html_generator import HTMLGenerator
from repo.reports.writter import ReportWritter

from models.member import Member
from models.manager import Manager

if __name__ == '__main__':
    username = 'erickmacena1'
    response = GithubClient.get_repos_by_user(username)

    if response['status_code'] == 200:
        repos = RepoParser.parse(response['body'])
        markdown_report = ReportsGenerator.build(MarkdownGenerator, repos)
        html_report = ReportsGenerator.build(HTMLGenerator, repos)
        ReportWritter.write(markdown_report)

        print(html_report)
        print(markdown_report)
    else:
        print(response['body'])

    member = Member('jao', 'jao@gmail.com')
    manager = Manager('gerente', 'gerente@gmail.com')

    print(member.members())

    print(member.work())
    print(manager.work())