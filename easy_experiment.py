import os
import subprocess
import uuid
import pathlib,shutil,json
import subprocess

def get_file_diff(file_path):
    """
    指定したファイルに対する最新のdiffを取得する関数
    """
    try:
        git_diff = subprocess.check_output(['git', 'diff',"HEAD",file_path]).decode('utf-8').strip()
    except subprocess.CalledProcessError:
        git_diff = "unknown"
    return git_diff

def get_git_hash():
    """
    Gitのハッシュを取得する関数
    """
    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
    except subprocess.CalledProcessError:
        git_hash = "unknown"
    return git_hash


def git_commit_all_unstaged(commit_message,experimentBranch = "experiments"):
    subprocess.run(["git", "checkout", experimentBranch], check=True)
    # 変更されたがステージングされていないファイルを検出
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    changed_files = [line[3:] for line in result.stdout.splitlines() if line.startswith("??") or line.startswith(" M")]

    # ステージングする
    if changed_files:
        subprocess.run(["git", "add"] + changed_files, check=True)

        # コミットメッセージ付きでコミット
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
    else:
        print("ステージングするファイルがありません。")

# 使用例
# git_commit_all_unstaged("すべての変更をコミットします")
import stat
def make_readonly_recursive(directory):
    # ディレクトリ以下を再帰的に処理
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            # 読み取り専用に変更
            os.chmod(file_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            # ディレクトリも読み取り専用に変更
            os.chmod(dir_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

class EasyExperiment:
    def __init__(self,parent_dir = "experiments",experiment_id = None) -> None:
        self.experiment_id = experiment_id if experiment_id is not None else self.generate_experiment_id()
        self.parent_dir = parent_dir
        self.save_dir = pathlib.Path(self.parent_dir)/pathlib.Path(self.experiment_id)
        self.save_dir.mkdir(exist_ok=False)
    def generate_experiment_id(self):
        self.experiment_id = str(uuid.uuid4())
        return self.experiment_id
    def generate_experiment_dir(self):
        self.save_dir.mkdir(parents=True,exist_ok=True)
    def start_experiment(self,filepath_list = [__file__]):
        for filepath in filepath_list:
            # diff = get_file_diff(filepath)
            hash = get_git_hash()
            self.generate_experiment_dir()
            with open(self.save_dir/pathlib.Path("hash"),mode="w") as f:
                f.write(hash)
            # with open(self.save_dir/pathlib.Path("diff"),mode="w") as f:
            #     f.write(diff)
            with open(filepath,mode="r",encoding="utf-8") as f:
                source = f.read()
            name = pathlib.Path(filepath).name
            with open(self.save_dir/pathlib.Path(name),mode="w") as f:
                f.write(source)
        make_readonly_recursive(self.save_dir)
        return self.experiment_id
    def write_explicit_parms(self,d:dict):
        with open(self.save_dir/pathlib.Path("prm.json"),mode="w") as f:
            json.dump(d,f)


class EasyExperiment2(EasyExperiment):
    def start_experiment(self, filepath_list=[],commit_message = None):
    # def start_experiment(self, commit_message = None):
        if commit_message is None:
            commit_message = self.experiment_id
        git_commit_all_unstaged(commit_message)
        return super().start_experiment(filepath_list)
    
if __name__ == "__main__":
    # a = EasyExperiment("")
    # a.start_experiment(__file__)
    a = EasyExperiment2()
    a.start_experiment()