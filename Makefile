.PHONY: aur-remote aur-pull aur-push aur-sync

aur-remote:
	git remote get-url aur >/dev/null 2>&1 || git remote add aur aur@aur.archlinux.org:wallpicker.git

aur-pull: aur-remote
	git subtree pull --prefix aur aur master

aur-push: aur-remote
	git subtree push --prefix aur aur master

aur-sync: aur-remote
	git subtree pull --prefix aur aur master
	git subtree push --prefix aur aur master
