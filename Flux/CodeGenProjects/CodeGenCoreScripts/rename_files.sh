# renames files and directories based on regex param passed
# Sample usage to replace spaces ' ' with hyphens '-' below
# 1. dont replace just show what will be renamed
# find-rename-regex ' /-/g'
# 2. actual rename
# find-rename-regex ' /-/g' -v
find_rename_regex() (
  set -eu
  find_and_replace="$1"
  # fix PATH : because -execdir has a drawback: find is opinionated & refuses to work  with -execdir if any relative paths found in PATH env var, e.g. ./node_modules/.bin will fail
  PATH="$(echo "$PATH" | gsed -E 's/(^|:)[^\/][^:]*//g')" \
  # rename is perl based - add LC_ALL=C to avoid locale warning
  LC_ALL=C find . -depth -execdir rename "${2:--n}" "s/${find_and_replace}" '{}' \;
  # more explanation:
  # -execdir option does a cd into the directory before executing the rename command, unlike -exec
  # -depth ensure that the renaming happens first on children, and then on parents, to prevent potential problems with missing parent directories
  # this will fail without execdir: rename 's/findme/replacement/g' acc/acc
)

