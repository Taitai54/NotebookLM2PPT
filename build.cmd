python -m build
@REM push to pypi
@REM twine upload --repository pypi dist/*.whl dist/*.tar.gz 