PS C:\xampp\htdocs\es-git-training> git status
On branch feat/ota-server
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   shodai-api/api/log.php
        modified:   shodai-api/index.php
        modified:   shodai-api/style.css

no changes added to commit (use "git add" and/or "git commit -a")
PS C:\xampp\htdocs\es-git-training> git add .
warning: in the working copy of 'shodai-api/api/log.php', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'shodai-api/index.php', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'shodai-api/style.css', LF will be replaced by CRLF the next time Git touches it
PS C:\xampp\htdocs\es-git-training> git commit -m "feat/add-height"
[feat/ota-server 7d35526] feat/add-height
 1 file changed, 3 insertions(+), 2 deletions(-)
PS C:\xampp\htdocs\es-git-training> git status
On branch feat/ota-server
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   shodai-api/style.css

no changes added to commit (use "git add" and/or "git commit -a")
PS C:\xampp\htdocs\es-git-training> git add .
warning: in the working copy of 'shodai-api/style.css', LF will be replaced by CRLF the next time Git touches it
PS C:\xampp\htdocs\es-git-training> git commit -m "feat/delete-height"
[feat/ota-server 8c94641] feat/delete-height
 1 file changed, 1 insertion(+), 1 deletion(-)
PS C:\xampp\htdocs\es-git-training> git push origin feat/ota-server
Enumerating objects: 11, done.
Counting objects: 100% (11/11), done.
Delta compression using up to 16 threads
Compressing objects: 100% (8/8), done.
Writing objects: 100% (8/8), 679 bytes | 339.00 KiB/s, done.
Total 8 (delta 6), reused 0 (delta 0), pack-reused 0 (from 0)
remote: Resolving deltas: 100% (6/6), completed with 3 local objects.
remote: 
remote: Create a pull request for 'feat/ota-server' on GitHub by visiting:
remote:      https://github.com/shodai1216/es-git-training/pull/new/feat/ota-server
remote: 
To https://github.com/shodai1216/es-git-training.git
 * [new branch]      feat/ota-server -> feat/ota-server
PS C:\xampp\htdocs\es-git-training> git remote -v
origin  https://github.com/shodai1216/es-git-training.git (fetch)
origin  https://github.com/shodai1216/es-git-training.git (push)
upstream        https://github.com/anhducad1111/es-git-training.git (fetch)
upstream        https://github.com/anhducad1111/es-git-training.git (push)
PS C:\xampp\htdocs\es-git-training> git remote -v
origin  https://github.com/anhducad1111/es-git-training.git (fetch)
origin  https://github.com/anhducad1111/es-git-training.git (push)
upstream        https://github.com/anhducad1111/es-git-training.git (fetch)
upstream        https://github.com/anhducad1111/es-git-training.git (push)
PS C:\xampp\htdocs\es-git-training> git push origin feat/ota-server
Enumerating objects: 11, done.
Counting objects: 100% (11/11), done.
Delta compression using up to 16 threads
Compressing objects: 100% (8/8), done.
Writing objects: 100% (8/8), 679 bytes | 679.00 KiB/s, done.
Total 8 (delta 6), reused 0 (delta 0), pack-reused 0 (from 0)
remote: Resolving deltas: 100% (6/6), completed with 3 local objects.
remote: 
remote: Create a pull request for 'feat/ota-server' on GitHub by visiting:
remote:      https://github.com/anhducad1111/es-git-training/pull/new/feat/ota-server
remote: 
To https://github.com/anhducad1111/es-git-training.git
 * [new branch]      feat/ota-server -> feat/ota-server