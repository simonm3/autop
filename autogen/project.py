import os
from setuptools import find_packages
import autopep8
from glob import glob
from .utils import subprocess_run, normpath

import logging

log = logging.getLogger()


class Project:
    """ a project for which we want to take actions such as generate a setup.py; publish docs; ormake a release """

    def __init__(self):
        # exclude files not in git
        self.gitfiles = subprocess_run("git ls-files").splitlines()

    def defaults(self):
        """ default params for setup """
        return dict(
            name=self.name(),
            description=self.description(),
            version=self.version(),
            url=self.url(),
            install_requires=self.install_requires(),
            packages=self.packages(),
            package_data=self.package_data(),
            include_package_data=True,
            py_modules=self.py_modules(),
            scripts=self.scripts(),
        )

    def create_setup(self):
        """ generate setup.py file """
        out = []

        # start
        out.append(
            '"""\n'
            "This file is automatically generated by the autogen package.\n"
            "Please edit the marked area only. Other areas will be\n"
            "overwritten when autogen is rerun.\n"
            '"""\n'
            "\n"
            "from setuptools import setup\n"
            "\n"
        )

        # params
        out.append("params = dict(\n")
        params = []
        for k, v in self.defaults().items():
            if isinstance(v, str):
                v = "'%s'" % v
            params.append("   %s=%s" % (k, v))
        out.append(",\n".join(params))
        out.append(")\n")
        out.append("\n")

        # bespoke
        out.append("########## EDIT BELOW THIS LINE ONLY ##########\n")
        bespoke = "\n\n"
        try:
            with open("setup.py") as f:
                lines = f.readlines()
                search = "EDIT BELOW THIS LINE ONLY"
                start = [i for i, s in enumerate(lines) if search in s][0]
                search = "EDIT ABOVE THIS LINE ONLY"
                end = [i for i, s in enumerate(lines) if search in s][0]
                bespoke = lines[start + 1 : end]
        except FileNotFoundError:
            pass
        except IndexError:
            raise Exception(
                "Markers are missing from edit section. Replace\n"
                "markers manually or delete setup.py before running\n"
                "autogen"
            )

        out.extend(bespoke)
        out.append("########## EDIT ABOVE THIS LINE ONLY ##########\n")
        out.append("\n")

        # finish
        out.append("setup(**params)")
        out = autopep8.fix_code("".join(out))

        # write to file
        with open("setup.py", "w") as f:
            f.writelines(out)
        log.info("created new setup.py")

    def release(self):
        """ publish new release to pypi and github """
        version = self.version()

        # release to git
        subprocess_run("git commit -a -m 'version update'")
        subprocess_run(f"git tag {version}")
        subprocess_run("git push")
        subprocess_run("git push --tags origin master")

        # release to pypi
        subprocess_run("python setup.py clean --all sdist bdist_wheel")
        subprocess_run(f"twine upload dist/*{version}*")

    def conda(self):
        """ todo release to conda """
        raise NotImplementedError

        # NOT TESTED, TAKES TIME TO RUN, NEEDS TO INCLUDE EACH PLATFORM SEPARATELY
        # with open("version") as f:
        #     version = f.read()
        # os.remove("condapack")
        # subprocess_run(f"conda skeleton pypi --output-dir condapack --version {version}")
        # subprocess_run("conda build condapack --output-folder condapack")
        # subprocess_run("anaconda upload condapack/win-64/*.tar.bz2")

    def name(self):
        """ name is folder name """
        return os.path.basename(os.getcwd())

    def description(self):
        """ first line of readme """
        try:
            readme = [
                f for f in os.listdir(os.getcwd()) if f.lower().startswith("readme")
            ][0]
            with open(readme, "r") as f:
                return f.readline().strip(" #\n")
        except:
            log.warning("no readme provided. setting description=name")
            return self.name()

    def version(self):
        try:
            with open("version") as f:
                version = f.read()
        except FileNotFoundError:
            version = "0.0.0"
        return version

    def update_version(self, level):
        """increment the level passed by one. version is in format level0.level1,level2

        :param level: 0, 1 or 2 for major, minor, patch update
        """
        version = self.version()

        # increment
        versions = [int(v) for v in version.split(".")]
        versions[level] += 1
        for i in range(level + 1, len(versions)):
            versions[i] = 0
        version = ".".join([str(v) for v in versions])

        # update
        with open("version", "w") as f:
            f.write(version)

    def url(self):
        """ url is github page for project """
        try:
            url = subprocess_run("git remote get-url origin").rstrip("\n")
            url = url.replace("ssh://git@", "https://")
            url = url.replace("git@", "http://")
        except:
            return ""
        return url

    def packages(self):
        """ packages in git """
        return find_packages(exclude=["_*"])

    def install_requires(self):
        """ all packages identifies by pipreqs """

        # create requirements.txt. force overwrite.
        command = f"pipreqs . --force"

        # ignore top level folders that are not packages (--ignore only looks at top level)
        packages = [p.split(".")[0] for p in find_packages() if not p.startswith("_")]
        folders = [f for f in os.listdir() if os.path.isdir(f)]
        excluded = list(set(folders)-set(packages))
        if excluded:
            excluded = ",".join(excluded)
            command = f"{command} --ignore {excluded}"
        subprocess_run(command)

        # remove version pinning
        with open("requirements.txt") as f:
            requirements = f.read().splitlines()
        unpinned = [r[: r.find("=")] for r in requirements]

        # remove invalid items. prob bug in pipreqs
        requires = [
            u
            for u in unpinned
            if not (u.endswith(".egg") or u.startswith("~") or u in ["setuptools"])
        ]

        # flag windows only packages
        # NOTE BUG IN PIP MEANS THIS IS IGNORED IN BINARY INSTALLS
        for package in ["xlwings", "pywin32"]:
            if package in requires:
                requires.remove(package)
                requires.append(f"{package};platform_system=='Windows'")

        return sorted(list(set(requires)))

    def py_modules(self):
        """ all git controlled in root ending .py """
        files = [
            f
            for f in os.listdir(os.getcwd())
            if os.path.isfile(f)
            and f in self.gitfiles
            and f.endswith(".py")
            and f not in ["setup.py"]
        ]
        modules = [f[:-3] for f in files]
        return sorted(modules)

    def package_data(self):
        """ all files in packages; git controlled; not ending .py """
        package_data = dict()
        folders = [p.replace(".", "/") for p in self.packages()]
        for folder in folders:
            package_files = [f"{folder}/{f}" for f in os.listdir(folder)]
            package_files = [
                f
                for f in package_files
                if os.path.isfile(f) and not f.endswith(".py") and f in self.gitfiles
            ]
            if package_files:
                package_data[folder] = [f[len(folder) + 1 :] for f in package_files]
        return package_data

    def scripts(self):
        """ files from scripts folder managed by git """
        folder = "scripts"
        if not os.path.isdir(folder):
            return
        files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f))
        ]
        files = [normpath(f) for f in files]
        files = set(files) & set(self.gitfiles)
        return sorted(list(files))
