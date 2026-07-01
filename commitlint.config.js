export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'chore', 'refactor', 'docs', 'style', 'test', 'perf', 'build', 'ci', 'revert'],
    ],
    'scope-empty': [2, 'always'],
    'subject-empty': [2, 'never'],
    'subject-case': [2, 'always', ['lower-case']],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 100],
  },
}
