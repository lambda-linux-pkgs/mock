%define _buildid .1

# next four lines substituted by autoconf
%define major 1
%define minor 1
%define sub 41
%define extralevel %{nil}
%define release_name mock
%define release_version %{major}.%{minor}.%{sub}%{extralevel}

%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

# mock group id allocate for Fedora
%global mockgid  135

Summary: Builds packages inside chroots
Name: mock
Version: %{release_version}
Release: 1%{?_buildid}%{?dist}
License: GPLv2+
Group: Development/Tools
Source: https://git.fedorahosted.org/cgit/mock.git/snapshot/%{name}-%{version}.tar.xz
URL: http://fedoraproject.org/wiki/Projects/Mock
BuildArch: noarch
Requires: python >= 2.6, yum >= 2.4, tar, pigz, python-ctypes, python-decoratortools, usermode
Requires: yum-utils
Requires: createrepo_c
Requires: pyliblzma
Requires(pre): shadow-utils
Requires(post): coreutils
Requires(post): %{_sbindir}/update-alternatives
Requires(preun): %{_sbindir}/update-alternatives
BuildRequires: python-devel, autoconf, automake

# bash-completion package is not yet available in AL/LL
%if 0%{?fedora} || 0%{?rhel} > 6
BuildRequires: bash-completion
%endif

# Lambda Linux patches
Patch1001: 1001-Add-support-for-Lambda-Linux-WIP.patch
Patch1002: 1002-Add-support-for-Amazon-Linux.patch

%description
For package support, please visit
https://github.com/lambda-linux-pkgs/%{name}/issues

Mock takes an SRPM and builds it in a chroot.

%package scm
Group: Development/Tools
Summary: Mock SCM integration module
Requires: mock = %{version}-%{release}, cvs, git, subversion, tar

%description scm
For package support, please visit
https://github.com/lambda-linux-pkgs/%{name}/issues

Mock SCM integration module.

%prep
%setup -q

# Lambda Linux patches
%patch1001 -p1
%patch1002 -p1

%build
autoreconf -vif
%configure
make

%install
rm -rf $RPM_BUILD_ROOT
make DESTDIR=$RPM_BUILD_ROOT install
mkdir -p $RPM_BUILD_ROOT/var/lib/mock
mkdir -p $RPM_BUILD_ROOT/var/cache/mock
ln -s consolehelper $RPM_BUILD_ROOT/usr/bin/mock

# compatibility symlinks
# (probably be nuked in the future)
pushd $RPM_BUILD_ROOT/etc/mock
ln -s epel-5-i386.cfg   fedora-5-i386-epel.cfg
ln -s epel-5-ppc.cfg    fedora-5-ppc-epel.cfg
ln -s epel-5-x86_64.cfg fedora-5-x86_64-epel.cfg
# more compat, from devel/rawhide rename
ln -s fedora-rawhide-i386.cfg fedora-devel-i386.cfg
ln -s fedora-rawhide-x86_64.cfg fedora-devel-x86_64.cfg
ln -s fedora-rawhide-ppc.cfg fedora-devel-ppc.cfg
ln -s fedora-rawhide-ppc64.cfg fedora-devel-ppc64.cfg
popd
echo "%defattr(0644, root, mock)" > %{name}.cfgs
find $RPM_BUILD_ROOT%{_sysconfdir}/mock -name "*.cfg" \
    | sed -e "s|^$RPM_BUILD_ROOT|%%config(noreplace) |" >> %{name}.cfgs

# just for %%ghosting purposes
ln -s fedora-rawhide-x86_64.cfg $RPM_BUILD_ROOT%{_sysconfdir}/mock/default.cfg

if [ -d $RPM_BUILD_ROOT%{_datadir}/bash-completion ]; then
    echo %{_datadir}/bash-completion/completions/mock >> %{name}.cfgs
    echo %{_datadir}/bash-completion/completions/mockchain >> %{name}.cfgs
elif [ -d $RPM_BUILD_ROOT%{_sysconfdir}/bash_completion.d ]; then
    echo %{_sysconfdir}/bash_completion.d/mock >> %{name}.cfgs
fi

%if 0%{?rhel} == 6
    # can be removed when yum-utils >= 1.1.31 lands in el6
    echo "config_opts['plugin_conf']['package_state_enable'] = False" >> $RPM_BUILD_ROOT%{_sysconfdir}/mock/site-defaults.cfg
%endif

%pre

# check for existence of mock group, create it if not found and add
# `ec2-user` to mock group
getent group mock > /dev/null || (groupadd -f -g %mockgid -r mock && usermod -a -G mock ec2-user)
exit 0

%post

# fix cache permissions from old installs
chmod 2775 /var/cache/mock

#
# We give higher priority to Amazon Linux
#
rm -f %{_sysconfdir}/%{name}/default.cfg

%{_sbindir}/update-alternatives \
  --install %{_sysconfdir}/%{name}/default.cfg \
  mock-default.cfg \
  %{_sysconfdir}/%{name}/ll-latest-x86_64.cfg 10

%{_sbindir}/update-alternatives \
  --install %{_sysconfdir}/%{name}/default.cfg \
  mock-default.cfg \
  %{_sysconfdir}/%{name}/amzn-latest-x86_64.cfg 20

%preun

if [ $1 -eq 0 ]; then
    %{_sbindir}/update-alternatives \
      --remove mock-default.cfg \
      %{_sysconfdir}/%{name}/ll-latest-x86_64.cfg

    %{_sbindir}/update-alternatives \
      --remove mock-default.cfg \
      %{_sysconfdir}/%{name}/amzn-latest-x86_64.cfg
fi

%files -f %{name}.cfgs
%defattr(-, root, root)

# executables
%{_bindir}/mock
%{_bindir}/mockchain
%attr(0755, root, root) %{_sbindir}/mock

# python stuff
%{python_sitelib}/*
%exclude %{python_sitelib}/mockbuild/scm.*

# config files
%dir  %{_sysconfdir}/%{name}
%ghost %config(noreplace,missingok) %{_sysconfdir}/%{name}/default.cfg
%config(noreplace) %{_sysconfdir}/%{name}/*.ini
%config(noreplace) %{_sysconfdir}/pam.d/%{name}
%config(noreplace) %{_sysconfdir}/security/console.apps/%{name}

# gpg keys
%dir %{_sysconfdir}/pki/mock
%config(noreplace) %{_sysconfdir}/pki/mock/*

# docs
%{_mandir}/man1/mock.1*
%{_mandir}/man1/mockchain.1*
%doc ChangeLog

# cache & build dirs
%defattr(0775, root, mock, 02775)
%dir /var/cache/mock
%dir /var/lib/mock

%files scm
%{python_sitelib}/mockbuild/scm.py*

%changelog
* Fri Jul 18 2014 Clark Williams <williams@redhat.com> - 1.1.41-1
- fix python 2.7 feature so we can run on rhel6

* Thu Jul 17 2014 Clark Williams <williams@redhat.com> - 1.1.40-1
- from Miroslav Suchý <msuchy@redhat.com>:
  - mock: Revert "revert 7ec6a1e9d202ab56fb31c914dbf7516c045e56ab" [BZ# 1103239]
  - configs: use final Centos 7 path in configs [BZ# 1108402]
  - configs: fix typo in fedora-rawhide-armhfp config [BZ# 1108847]
  - mockchain: use getuid() instead of getgid() [BZ# 1108265]
  - configs: check gpg key of packages from Fedora, Centos, Epel
  - plugins: disable package_state by default on el6
  - make /etc/mtab symlink to /proc/self/mounts [BZ# 1116158]
  - do not list pki files twice
  - deploy etc/pki to buildroot
- from Michael Simacek <msimacek@redhat.com>:
  - mock: do not allow config scripts to regain root priviledges
- from Igor Gnatenko <i.gnatenko.brain@gmail.com>:
  - Add F21 configs
  - Change releasever to 22 for rawhide

* Wed May 21 2014 Clark Williams <williams@redhat.com> - 1.1.39-1
- configs: update epel-7 koji repo to use correct URL
- from Ken Dreyer <ktdryer@ktdryder.com>
  - Use RHEL 7 RC mirrorlist URLs
from Miroslav Suchý <msuchy@redhat.com>
  - add support for subscription-manager (RHSM)
  - expand tabs for better readablity
  - cut of everything after decimal point, if there is some [BZ# 1098477]
  - better code readablity
  - clarify the log messages
  - use metalink instead of mirrorlist in yum config
  - set LC_MESSAGE to C before executing command [BZ# 519258]
  - use ctypes.get_errno() instead of ctypes.c_int.in_dll(_libc, "errno")
  - revert 7ec6a1e9d202ab56fb31c914dbf7516c045e56ab (python 2.4 workarounds)
  - buildroot and %clean is not needed for el6 and fedoras
  - description should always end with dot
  - remove shebang from mockbuild/mounts.py
  - %defattr is not needed since rpm 4.4
  - remove el5 conditional
  - use createrepo_c which is much faster
  - whitespace fixes
  - remove unused variables: 'username' and 'hdr'
  - better logging of kernel version [BZ# 1048826]
  - partially revert 9db6edb33cc34a450e762eb5d2bedf9067ebc419 [BZ# 1034805]
  - teach mockchain about ftp [BZ# 1061776]
from Jerry James <loganjerry@gmail.com>
  - fix post scriptlet to deal with rawhide [BZ# 1083689]

* Mon Mar 31 2014 Clark Williams <williams@redhat.com> - 1.1.38-1
- revert commit 34d0b1d815e4 for quoting (breaks fedora-review)

* Thu Mar 27 2014 Clark Williams <williams@redhat.com> - 1.1.37-2
- fix el6 requires for yum-utils

* Mon Mar 24 2014 Clark Williams <williams@redhat.com> - 1.1.37-1
- fix thinko in test script for running configs
- plugins: turn off package_state plugin by default
- fix automake to use 'xz' compression
- additional commits needed by scm commit
- elevate privs when accessing the chroot rpmdb [BZ# 1051474]
- quote --shell args like a shell [BZ# 966144]
- from Tuomo Soini <tis@foobar.fi>
  - Fix for race in directory creation [BZ# 1052045]
- from Peter Jönsson <peter.jonsson@klarna.com>
  - Add support for creating tarballs with scm data still inside
- from Tomas Kopecek <tkopecek@redhat.com>
  - internal_dev_setup option used consistently
- from Dennis Gilmore <dennis@ausil.us>
  - add rawhide aarch64 config
  - remove sparc rawhide configs, she be dead
- from Ville Skyttä <ville.skytta@iki.fi>
  - Use $(mocketcdir) in install-data-hook instead of duplicating its value
  - Use xz tarball to save a bit of space
  - Clean up unused imports
  - Install bash completion to proper dir with bash-completion 2
  - Remove Fedora 18 configs
  - Use install @foo instead of groupinstall foo in chroot_setup_cmd
- from Rodrigo Dias Cruz <rodrigodc+redhatbugzilla@gmail.com>
  -  fix scm problem with specfiles using rpm macros [BZ# 1056271]
- from Tomas Kopecek <tkopecek@redhat.com>
  - avoid undefined variable error in try/finally block [BZ# 1063275]

* Wed Feb  5 2014 Clark Williams <williams@redhat.com> - 1.1.36-1
- configs: first cut at epel-7 configs for x86_64 and ppc64
- Add 'extra_chroot_dirs' config option
- use repoquery --installroot to avoid yum cache corruption [BZ# 1029352 and 985681]
- mockchain: avoid special characters in repoid [BZ# 1034805]
- from Jon Disnard <jdisnard@gmail.com>:
  - implement autoreconf call in build phase of mock rpm [BZ# 926154]
  - fix --copyout by temporary drop and restore of privs [BZ# 1002142]
- from Dennis Gilmore <dennis@ausil.us>:
  - rawhide and f19/f18 is hardware floating point only for arm, drop the unneeded configs
- from Yann Droneaud <yann@droneaud.fr>:
  - pass root environment to repoquery calls for proxy config [BZ# 974499]
- from Miroslav Suchý <msuchy@redhat.com>:
  - add releasever config option to configs [BZ# 1056039]

* Tue Nov  5 2013 Clark Williams <williams@redhat.com> - 1.1.35-1
- modified %%post logic to set default config correctly

* Tue Oct 29 2013 Clark Williams <williams@redhat.com> - 1.1.34-1
- fixed specfile to include mass rebuild changelog entry
- package_state: drop privs when writing available_packages data [BZ# 916685]
- unconditionally update default.cfg on install [BZ# 858822]
- attempt to make mock more EL5 friendly [BZ# 949616]
- do not ignore missing dependencies [BZ# 955478]
- set the group defined in chrootgid [BZ# 953519]
- add the --nocheck option to mock [BZ# 1015790]
- raise privs before deleting rpm db files in chroot [BZ# 973617]
- clean up orphan processes even if chroot not cleaned [BZ# 972868]
- do not remove the chroot builddir if not cleaning the chroot [BZ# 483486]
- use root object environment in package_state plugin [BZ# 921221]
- Pass values of --plugin-option through literal_eval [BZ# 1018359]
- add default mode to mount in tmpfs plugin [BZ# 598257]
- exit mockbuild.util.logOutput() when child process dies [BZ# 885405]

* Wed Aug 21 2013 Clark Williams <williams@redhat.com> - 1.1.33-1
- removed f17 configs
- added f20 configs
- fixed mockchain to use mock config default setup [BZ# 962573]
- remove bogus lockfile dir in _setupDirs() [BZ# 894305]

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.1.32-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Thu Apr 18 2013 Clark Williams <williams@redhat.com> - 1.1.32-1
- fixed post scriptlet to use correct keyword to getent

* Fri Apr 12 2013 Clark Williams <williams@redhat.com> - 1.1.31-1
- removed f16 configurations files
- selinux plugin: modify to catch yum-builddep in callback [BZ# 923927]
- fix logging assumption in main mock file [BZ# 912624]
- initial cut at chroot_scan plugin [BZ# 441090]
- updated specfile to use static mock gid 135
- from Marko Myllynen <myllynen@redhat.com>:
  - separate scm module into separate package [BZ# 798367]
  - scm plugin: Handle filenames w/ spaces in SCM/git  [BZ# 915264]
  - scm plugin: if tar supports --exlcude-vcs use it [BZ#  824848]
- from Shad L. Lords <slords@lordsfam.net>:
  - mounts plugin: removed redundant '-t' specified for vfstype [BZ# 910857]
- from Justin Lewis Salmon <jsalmon@cern.ch>:
  - root cache plugin: add the --cache-alternations option [BZ# 905363]

* Thu Mar 28 2013 Clark Williams <williams@redhat.com> - 1.1.30-1
- beef up the logic to remove RPM lock files inside the chroot
- add backup-before-clean configuration options [BZ# 799639]
- added fedora-19 config files [BZ# 922268]
- package_state plugin: don't run repoquery when offline [BZ# 927496]

* Fri Feb 22 2013 Clark Williams <williams@redhat.com> - 1.1.29-1
- move CLONE_NEWUTS to extended unshare options [BZ# 890695]
- make epel-5-* config files safe to eval [BZ# 903686]
- remove CLONE_NEWPID (for now) from unshare(2) call [BZ# 894623]
- initialize package_state_opts so that package_state plugin will work
- change default tests environment to be -i386
- From Tim Woods <timw.fedora@gmail.com>
  - Fix mockchain repo id calculation [BZ# 880849]
- From Tzafrir Cohen <tzafrir.cohen@xorcom.com>
  - Fix most bashism in test scripts
- From Seth Vidal <skvidal@fedoraproject.org>:
  - mockchain: allow for a non-username tmpdir prefix
  - mockchain: comma is a protected character make it _ instead

* Mon Sep 24 2012 Clark Williams <williams@redhat.com> - 1.1.28-1
- add updates-testing stanza to fedora-1x-*.cfg [BZ# 610826]
- modify scrub to handle non-existant chroots [BZ# 860368]

* Fri Sep  7 2012 Clark Williams <williams@redhat.com> - 1.1.27-1
- fixed configs test report to indicate configuration failure total
- remove dead code, unused array 'legal_arches'
- add an 'age_check' parameter to root_cache
- deal with NFS home directories and root_cache issues [BZ# 649192]
- from Mike Miller <mtmiller@ieee.org>:
  - Fix mock kernel version comparison [BZ# 847473]
- from Mathieu Bridon <bochecha@fedoraproject.org>:
  - fix various start/finish state problems [BZ# 835633]
- from Colin Walters <walters@redhat.com>:
  - add CLONE_NEWPID and CLONE_NEWIPC to unshare call [BZ# 851340]

* Fri Aug 10 2012 Dennis Gilmore <dennis@ausil.us> - 1.1.26-2
- add f18 configs
- add rawhide s390 config

* Mon Aug  6 2012 Clark Williams <williams@redhat.com> - 1.1.26-1
- move the fedora-17-ppc* configs into the configs directory

* Tue Jul 31 2012 Clark Williams <williams@redhat.com> - 1.1.25-1
- From Karsten Hopp <karsten@redhat.com>:
  - added ppc and ppc64 configs for fedora 17

* Fri Jul 27 2012 Clark Williams <williams@redhat.com> - 1.1.24-1
- Fixed error when calling os.getlogin() [BZ# 843434]
- removed fedora-15 config files
- from Matt McCutchen <matt@mattmccutchen.net>:
  - allowed common options to be added to yum commands [BZ# 734576]
- from Ville Skyttä <ville.skytta@iki.fi>:
  - added mockchain completion
- from Seth Vidal <skvidal@fedoraproject.org>:
  - added package_state_plugin

* Thu Jun  7 2012 Clark Williams <williams@redhat.com> - 1.1.23-1
  - modified startup code to only set mock group [BZ# 809676]
  - add CLONE_NEWUTS to unshare(2) call [BZ# 818445]
  - from Seth Vidal <skvidal at fedoraproject.org>:
    - add mockchain to mock [BZ# 812477]
  - from Marko Myllynen <myllynen@redhat.com>:
    - fix write_tar check in scm.py [BZ# 828677]
  - from Masatake YAMATO <yamato@redhat.com>:
    - added option to set a plugin parameter value [BZ# 754321]

* Thu Mar 29 2012 Clark Williams <williams@redhat.com> - 1.1.22-1
- fix SCM problem with SSH_AUTH_SOCK [BZ# 803217]
- From Chris St Pierre <chris.a.st.pierre@gmail.com>:
  - allow chroot group to be configure option

* Wed Feb  8 2012 Clark Williams <williams@redhat.com> - 1.1.21-1
- from Dennis Gilmore <dennis@ausil.us>
  - add Fedora 17 mock configs
  - have configs reflect the dropping of dist- for koji repos
  - add configs for arm hardware floating point

* Mon Jan 30 2012 Clark Williams <williams@redhat.com> - 1.1.20-1
- changed createrepo invocation to not be done inside the chroot [BZ# 783926]
- changed [local] repo definitions in f16+ configs [BZ# 753735]
- from Ville Skyttä <ville.skytta@iki.fi>
  - Allow setting https, ftp, and no proxy in addition to http.

* Mon Jan  2 2012 Clark Williams <williams@redhat.com> - 1.1.19-2
- fix missing files from Makefile.am

* Mon Jan  2 2012 Clark Williams <williams@redhat.com> - 1.1.19-1
- fix dangling symlink when using SCM [BZ# 758781]
- remove setting TMPDIR in chroot environment [BZ# 769728]
- add code to allow global proxy in chroot [BZ# 766199]
- explicitly set unprivileged umask in --shell [BZ# 747119]
- add bind-mount config to create sourcedirs [BZ# 706174]
- move mount management into classes
- update environment management code

* Sat Nov 26 2011 Clark Williams <williams@redhat.com> - 1.1.18-1
- modify creation of default.cfg link to force creation if the
  symlink exists but doesn't point to a valid config [BZ# 741145]
- remove TZ from default environment [BZ# 754701]
- unbuffer output from --chroot command [BZ# 744761]
- added -debug stanzas in configs [BZ# 610823]
- report package contents of chroot after init [BZ# 736858]
- add _umountall() call to clean [BZ# 502922]
- updated release checklist overview and 1.1 checklist
- add code to tmpfs plugin to try a force umount on umount fail
- add 'lazy' option (-l) to umount
- prevent exceptions when showing installed packages on EPEL-4
- deleted unused (or cannot be used) configs
- from Davi Arnaut <davi.arnaut@gmail.com>
  - set chroot environment variables from config files [BZ# 753179]

* Mon Oct 31 2011 Clark Williams <williams@redhat.com> - 1.1.17-1
- fix borken shell argument handling [BZ# 750075]
- from Marko Myllynen <myllynen@redhat.com>:
  - Fix SCM integration on RHEL 5 [BZ# 749518]
- from Ville Skyttä <ville.skytta@iki.fi>:
  - bash completion fixes

* Fri Oct 21 2011 Clark Williams <williams@redhat.com> - 1.1.16-1
- modified bind_mount and tmpfs plugins to use hooks for shell and chroot
- refactored --shell and --chroot commands [BZ# 619533,728004,745550]
- added input validation for --buildsrpm [BZ# 743173]
- ensured configs don't have execute bit set [BZ# 744013]
- modified root cache pluging to not cache bind mounts [BZ# 744727]
- removed invalid excludes from epel-{4,5}-x86_64 configs [BZ# 533762]
- From Marko Myllynen <myllynen@redhat.com>:
  - Set HOME properly when doing SCM checkouts [BZ# 745394]
  - Support for setting timestamps for Git checkouts [BZ# 745396]
- From Yury V. Zaytsev <yury@shurup.com>:
  - fix incorrect-fsf-address rpmlint warning [BZ#741068]
- From Jan Vcelak <jvcelak@redhat.com>:
  - resolve SELinux filesystem mountpoint [BZ# 734781]

* Fri Sep 23 2011 Clark Williams <williams@redhat.com> - 1.1.15-1
- Fixed logging issues due to namespace change [BZ# 740232,739550,739972]
- Fixed error removing old RMP db files [BZ# 738052]
- From Yury V. Zaytsev <yury@shurup.com>:
  - SELinux plugin uses Python 2.5 syntax [BZ# 740327]
  - Fix inconsistent permissions in specfile [BZ# 715286]

* Fri Sep  9 2011 Clark Williams <williams@redhat.com> - 1.1.14-1
- From Toshio Ernie Kuratomi <a.badger@gmail.com>
  - Fix install path of mockbuild module and default path to module dir

* Thu Sep  8 2011 Clark Williams <williams@redhat.com> - 1.1.13-1
- add custom exception for unshare(2) failures
- change getLog().warn to getLog().warning for consistency
- fix namespace collision with python-mock [BZ# 601725]
- from Kirby Zhou <kirbyzhou@sogou-inc.com>
  - remove rpmdb files before rebuilding SRPM [BZ# 719008]
- from Marko Myllynen <myllynen@redhat.com>
  - integrate mock with RHN
- from Giam Teck Choon <choon@choon.net>
  - add support for passing options to yum-buildep via mock cfg

* Tue Jul 26 2011 Clark Williams <williams@redhat.com> - 1.1.12-1
- remove f13 configs
- added exception for unshare(2) failures [BZ# 718714]
- added back 'newinstance' mount option to devpts (with symlink logic)
- fixed epel-6-* configurations [BZ# 679885, 719740]
- from Matt Domsch <Matt_Domsch@dell.com>
  - tmpfs plugin typo fix

* Wed Jun 22 2011 Clark Williams <williams@redhat.com> - 1.1.11-1
- remove 'newinstance' mount parameter from devpts filesystem mount (BZ# 711175)
- modify --chroot command to print command output
- update the python requirement to >= 2.6 for 1.1.x mock branch
- updated build procedure using fedpkg
- added Fedora 16 configuration files
- from James Laska <jlaska@redhat.com>
  - fix log message typo in SELinux plugin
- from Yury V. Zaytsev <yury@shurup.com>
  - Fix inconsistent permissions fixing on /var/cache/mock in SPEC template (BZ 715286)

* Fri May 13 2011 Clark Williams <williams@redhat.com> - 1.1.10-1
- raise exception if running mock and user not member of mock group (BZ# 630791)
- call setsid() to kill controlling terminal in chroot (BZ# 672713,501096)
- Went back to creating /dev/tty and /dev/ptmx in all chroots (BZ# 683111)
- Fixed problem where mock was not constrained to the chroot (BZ# 669733)
- Fix typo in /dev/tty creation code for EPEL{4,5} (BZ# 675803)
- From Marko Myllynen <myllynen@redhat.com>:
  - updated SCM integration (BZ# 670453)
- from Masatake YAMATO <yamato@redhat.com>:
  - fixed invocation typo in exception.py (BZ# 634555)
- From Jan Vcelak <jvcelak@redhat.com>:
  - updated selinux plugin (BZ# 573111, 667190)
- From Levente Farkas <lfarkas@lfarkas.org>:
  - adding missing macro for epel-5 configs (BZ# 695298)
- From  Mathieu Bridon <bochecha@fedoraproject.org> and
        Remi Collet <fedora@famillecollet.com>:
  - fix chroot cleanup issues (BZ# 668222)
  - fix ccache ownership issues (BZ# 700983)
- From Dan Horák <dan@danny.cz>:
  - added s390 back as legal arch for s390x (BZ# 678047)
- From Ville Skyttä <ville.skytta@iki.fi>:
  - Fixes shell escaping issue by using tuples rather than strings

* Fri Feb 18 2011 Clark Williams <williams@redhat.com> - 1.1.9-1
- fix createrepo generated root-owned repository data (BZ# 668278)
- commented out /dev/tty handling code in backend.py (BZ# 609201)
- from Ville Skyttä <ville.skytta@iki.fi>
  - Use completion goodies from bash-completion >= 1.2 if available.
  - Add --scm-enable and --scm-option to bash completion.
  - Delete trailing whitespace.
  - Add --install bash completion.
  - Make --enable/disable-plugin completion work again.
- From Jesse Keating <jkeating@redhat.com>
  - Make "dist" for rawhide configs be "rawhide" (BZ# 506157)
  - Revert "turn off updates-released repository for fedora-14 configs"
- From Mike McLean <mikem@redhat.com>
  - fix typo in el4/5 /dev/tty creation (fh ticket #13, mwhiteley)
- From Dennis Gilmore <dennis@ausil.us>
  - Revert "disable the updates repos for F-15  they dont yet exist"
  - sparc64 boxes can build 32 bit sparc stuff
  - add rawhide arm config
  - use the s390 mirrorlists for s390 configs
  - disable the updates repos for F-15  they dont yet exist
  - add the f15 mock configs

* Fri Dec 17 2010 Clark Williams <williams@redhat.com> - 1.1.8-1
- corrected examples section of the mock.1 man page
- added logging for 'install' and 'update' commadns (BZ# 594477)
- added log file of root cache creation (BZ# 444796)
- added logging to the scrub command
- added unlockBuildRoot() method to clean up build root lockfile
- added retry logic to mock.util.rmtree
- removed fedora-12 config files
- From Michael Hampton <error@ioerror.us>:
  - Add -f (force) option to userdel when recreating mockbuild user (BZ# 662223)
- From Marko Myllynen <myllynen@redhat.com>:
  - Integrate Mock with SCMs (CVS/Git/SVN)
  - document SCM build options in usage and man page
- From Masatake YAMATO <yamato@redhat.com>:
  - add runtime location of plugins (BZ# 634224)

* Mon Dec 13 2010 Clark Williams <williams@redhat.com> - 1.1.7-1
- add 'legal_host_arches' config option to configs (BZ# 622792)
- add root check and group check (BZ# 662223)
- from Ville Skyttä <ville.skytta@iki.fi>:
  - Try to set up an appropriate default.cfg symlink at post install time
  - Clean up disttag usage
  - Drop obsolete and nonfunctional F-8 bits from specfile
  - Drop no longer used requiresTextFromHdr() and uniqReqs()
  - Install build deps with yum-builddep
  - Add comment why binary packages are built with --nodeps

* Thu Oct 14 2010 Clark Williams <williams@redhat.com> - 1.1.6-1
- replace call to perl with native python edit function
- change permissions of selinux plugin 'filesystems' file
- from Ville Skyttä <ville.skytta@iki.fi>:
  - Find out completions for --*-plugin dynamically
  - Keep $COLUMNS in consolehelper environment for --help formatting
  - Document --scrub, --enable-plugin, and --disable-plugin
  - Fix option name in --enable-plugin/--disable-plugin error string
  - Add --scrub completion
  - Complete on *.spm (*.src.rpm are sometimes named like that e.g. in SUSE)
  - Fix buildsrpm() docstring
  - Error message improvements

* Fri Sep 17 2010 Clark Williams <williams@redhat.com> - 1.1.5-1
- fix typo in exception.py
- add cmpKernelEVR function to compare kernel versions (BZ# 526414)
- change selinux plugin to use tempfilej
- added commandline argument checking for --buildsrpm (BZ# 605800)
- create empty faillog and lastlog in <chroot>/var/log (BZ# 585973 & 633435)
- changed copyin/copyout prints from debug to info
- from Alan Franzoni <mailing@franzoni.eu>:
  - reworked the root object _umountall() method
- fix epel4 chroot cleanup and umountall issue
- add exception trapping code to _unlock_and_rm_chroot() method

* Mon Aug 09 2010 Clark Williams <williams@redhat.com> - 1.1.4-1
- pass selinux status to mock.util.rmtree() (BZ# 614440)
- change integer constants to symbolic errno constants in util.py
- from Paul Howarth <paul@city-fan.org>
  - update packages after unpacking root cache (BZ# 557526)
  - noarch is always a legal arch (BZ# 622170)
  - exclude bind-mounted cache dirs from root cache
  - retain order of umount commands (BZ# 620825)
  - add i586 as legal build target (BZ# 622544)

* Tue Aug 03 2010 Clark Williams <williams@redhat.com> - 1.1.3-1
- fix umount ordering problem with selinux plugin (BZ# 620825)
- setup SELinux state properly (BZ# 620143)

* Fri Jul 30 2010 Clark Williams <williams@redhat.com> - 1.1.2-1
- From Jan Vcelak <jvcelak@redhat.com>:
  - added selinux plugin
- From Kalev Lember <kalev@smartlink.ee>:
  - added max_fs_size parameter for tmpfs plugin
- From Ricky Zhou <rzhou@redhat.com>:
  - allow --sources to specify either single file or directory (BZ# 510409)
- From Dennis Gilmore <dennis@ausil.us>:
  - update the epel-6 mock configs to point at the beta2 mirrorlist urls
- From  Paul B. Schroeder <paulbsch@haywired.net>:
  - add the --scrub option for cleaning up cache (BZ# 450726)
- added f14 configs
- added symlink from /proc/self/fd to /dev/fd in the chroot (BZ# 526414)
- added i686 architecture
- added logic to detect invalid architecture combinations (BZ# 607144)
- added description of how to add user to the mock group (BZ# 570434)
- deleted fedora-10 and fedora-11 configs
- moved rpmdb clean block so that it works with --offline
- changed from referencing defaults.cfs to site-defaults.cfg (BZ# 600487)
- fix cachefile generation filtering logic
- filter out proc,sys,and dev from cache file creation

* Fri May 14 2010 Clark Williams <williams@redhat.com> - 1.1.1-1
- patch from Seth Vidal <skvidal@fedoraproject.org> to handle
  rpmdb cache issue (BZ#591741)

* Thu Mar 11 2010 Jesse Keating <jkeating@redhat.com> - 1.1.0-1
- Make the createrepo command arguments optional
- Make the createrepo call disabled by default

* Fri Feb 19 2010 Clark Williams <williams@redhat.com>- 1.0.6-1
- added code to check for SELinux being enabled or disabled
  and avoid calling 'chcon' if disabled
- add conditional Require of python-hashlib if building for
  the EL5 distro

* Wed Feb 17 2010 Clark Williams <williams@redhat.com>- 1.0.5-1
- from Jesse Keating <jkeating@redhat.com>:
  - fixed 'useradd' option conflict with EPEL (-N vs -n)
  - added Fedora 13 configs

* Wed Feb 10 2010 Clark Williams <williams@redhat.com>- 1.0.4-1
- added patch from Seth Vidal <skvidal@fedoraproject.org> to
  automatically run createrepo on generated rpms

* Mon Jan 18 2010 Clark Williams <williams@redhat.com>- 1.0.3-1
- add logic for handling --unpriv with --shell (BZ# 522505)

* Wed Dec 23 2009 Clark Williams <williams@redhat.com>- 1.0.2-1
- added IPv6 localhost entry for default /etc/hosts (BZ# 545435)
- removed output of gethostname() in IPv4 localhost entry as this
  caused koji problems and cause 'localhost' to be put into generated
  rpms, rather than the output of hostname
- add code to setup /dev/pts differently on EL* than on FC* hosts

* Wed Nov 25 2009 Clark Williams <williams@redhat.com>- 1.0.1-1
- Patch from Paul Howarth to fix intermittent problems generating
  root cache tarball (BZ# 540997)

* Mon Nov 23 2009 Clark Williams <williams@redhat.com>- 1.0.0-1
- modified pty devpts mount code to actually work (BZ# 510183)
- deleted F9 configs
- version bump to 1.0.0

* Fri Nov 13 2009 Clark Williams <williams@redhat.com>- 0.9.20-1
- conditionalized import of uuid to avoid failure on RHEL5
- added autoconf/automake mojo to prefer using rpmbuild-md5 for
  cross-platform rpm compatibility

* Thu Nov  5 2009 Jesse Keating <jkeating@redhat.com>- 0.9.19-1
- Fix target arch for i386 on 12 and rawhide

* Thu Nov  5 2009 Jesse Keating <jkeating@redhat.com>- 0.9.18-1
- Update for Fedora 12 and 13 configs
- Patch from dgilmore to clean up epel configs
- Update configs for new koji static-repo locations
- Don't automatically update the chroot in a --no-clean scenario

* Wed Jul  8 2009 Clark Williams <williams@redhat.com>- 0.9.17-1
- Patch from Jakub Jelinek <jakub@redhat.com> for mounting
  /dev/pts correctly in the chroot (BZ# 510183)
- raise exception when --shell specified for uninitialized chroot
  (BZ# 506288)
- add directory and infrastructure to allow dbus to run inside
  chroot (BZ# 460574)
- patch from Levente Farkas <lfarkas@lfarkas.org> to fix exclude
  in EPEL 5 x86_64 config

* Mon May 11 2009 Jesse Keating <jkeating@redhat.com> - 0.9.16-1
- Make F11 and rawhide build i586 on i386 targets.

* Mon May 11 2009 Jesse Keating <jkeating@redhat.com> - 0.9.15-1
- Add configs for F11 (jkeating)

* Mon Feb 02 2009 Clark Williams <williams@redhat.com> - 0.9.14-1
- logging cleanup (mikem)
- add new exception for resultdir not available (mebrown)
- moved mock cache dir to /var/cache/mock (williams)
- added version variable and version banner to logs (williams)
- removed import of popen2 to whack deprecated message (williams)
- prevent disabling ccache on epel-5 (tmz)
- added configs for sparc and s390 (dgilmore)
- fixed git log command used in build (tmz)
- added copy of spec/sources for building srpms (mebrown)
- changed unlink to rmdir (mebrown)
- set HOME directory globally (mikeb)
- commented out privlege drop in --copyin (williams)

* Thu Nov 06 2008 Jesse Keating <jkeating@redhat.com> - 0.9.13-1
- Add configs for F10 (jkeating)

* Tue Oct 14 2008 Clark Williams <williams@redhat.com> - 0.9.12-1
- internal setarch support for s390/s390x (mikem)
- Refer to the .newkey location of current Fedora 8/9 updates. (jkeating)
- [bz458234] Picked up corrected patch (pmatilai)

* Thu Sep  4 2008 Clark Williams <williams@redhat.com> - 0.9.11-1
- added workarounds for rawhide rpm (BZ 455387 and 458234)
- disabled tmpfs plugin on epel-4-x86_64
- fixed autotools breakage in configure.ac

* Tue May 20 2008 Jesse Keating <jkeating@redhat.com> - 0.9.10-1
- added fix for building F-8 mock (clark)
- Update epel configs

* Tue Apr 22 2008 Jesse Keating <jkeating@redhat.com> - 0.9.9-1
- Update config files for Fedora 9
- Comment out multilib excludes, no longer needed in F9+ with yum multilib changes

* Mon Mar 31 2008 Jesse Keating <jkeating@redhat.com> - 0.9.8-1
- modify rootcache logic to rebuild cache if config files have newer timestamp
- For Fedora 8 and higher, use priority failover method
- Point to the correct static-repo for rawhide stuff.
- Move "devel" to "rawhide" to match current Fedora naming schemes.

* Thu Jan 31 2008 Michael Brown <mebrown@michaels-house.net> - 0.9.7-1
- redo mock.util.do() to use python subprocess module, which should be
  much more maintainable than our old homegrown code.
- Fix exclude= lines once again. Yum fnmatch parser doesn't understand [!x]
  notation
- add --unpriv and --cwd options to run chroot commands without elevated privs
  and in a specific working directory (under the root).
- mount all filesystems when running chroot commands
- remove redundant ccache init since we now source /etc/profile.d/ccache.sh

* Wed Jan 16 2008 Clark Williams <williams@redhat.com> - 0.9.6-1
- renamed configs and put compat symlinks in place
- misc cleanups (whitespace fixes, info messages, etc.)
- tmpfs plugin fix
- split --target and --arch command line arguments
- changed from -l to --login on bash invocations
- create /dev/full in chroot

* Thu Dec 20 2007 Michael Brown <mebrown@michaels-house.net> - 0.9.5-1
- really fix file-based BuildRequires

* Wed Dec 19 2007 Michael Brown <mebrown@michaels-house.net> - 0.9.4-1
- Result dir was not honoring --uniqueext=
- make rpmbuild run under a chroot login shell
- mock is now noarch due to drop of all binary components
- add tmpfs plugin (disabled by default)
- slightly more friendly logs.

* Fri Dec 14 2007 Clark Williams <williams@redhat.com> - 0.9.3-1
- added '--copyin' and '--copyout' modes
- added makeChrootPath() method to Root
- replaced most ad hock usages of .rootdir with makeChrootPath()
- updated man page && added test cases
- added 'help' target to Makefile.am

* Thu Dec 13 2007 Michael Brown <mebrown@michaels-house.net> - 0.9.2-1
- add '--update' mode
- fix '--shell' mode

* Tue Dec 11 2007 Michael Brown <mebrown@michaels-house.net> - 0.9.1-1
- fix 'mock shell' command when passing more than one arg.
- add --orphanskill mode which only does orphankill
- make 'mock --shell' noninteractive and logged to root.log
- fix for file-based BuildRequires
- add sparcs to constant list for auto-setarch

* Tue Dec 11 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.17-1
- fix 'mock shell' command when passing more than one arg.
- add --orphanskill mode which only does orphankill
- make 'mock --shell' noninteractive and logged to root.log
- fix for file-based BuildRequires
- add sparcs to constant list for auto-setarch

* Sun Dec 09 2007 Michael Brown <mebrown@michaels-house.net> - 0.9.0-1
- drop suid helper and use consolehelper instead.
- add unshare() call rather than clone(CLONE_NEWNS...)

* Sun Dec 09 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.16-1
- drop FC6 configs. FC6 no longer supported
- add --trace cmdline parameter
- make logs slightly less verbose

* Wed Dec 05 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.15-1
- fix traceback when root cache doesn't exist.
- add "--with", "--without", and "--define" cmdline parameters which are passed
  to rpmbuild (courtesy Todd Zullinger)

* Tue Dec 04 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.14-1
- fix traceback when cache dir was not found

* Tue Dec 04 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.13-1
- brown-paper-bag bug where built rpm didn't work due to lack of path
  substitution in mock.py

* Mon Dec 03 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.12-1
- fix builds of multiple srpms
- fix 'mock install'
- use python-decoratortools for better python 2.3 back compat

* Thu Nov 29 2007 Clark Williams <williams@redhat.com> - 0.8.11-1
- fixes from mebrown:
-   added back -q and -v flags
-   print yum output by default
-   added --offline option
-   cleaned up uid handling

* Mon Nov 26 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.10-1
- fix 'shell' command
- fix a couple different selinux avc denial messages (didnt affect functionality)

* Tue Nov 20 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.9-1
- Fixes so that mock will run cleanly on RHEL5
- Add glib-devel.i386, glib2-devel.i386 to yum exclude list as it breaks
  builds.
- Add backwards-compatibility code for old-style 'automatically assume rebuild'
  convention
- automake symlink accidentally included in tarball rather than file
  (py-compile)
- update manpage

* Mon Nov 19 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.8-1
- make it run correctly when called by the 'root' user
- internal_setarch: optionally run 'setarch' internally. This
  eliminates the need to run "setarch i386 mock ..." when building on
  target_arch != build_arch. This is turned on by default. Limitations:
  must have 'ctypes' python module available, which is only available
  by default in python 2.5, or as an extension module in <= 2.4.
  If the 'ctypes' module is not available, this feature will be
  disabled and you must manually run 'setarch'.
- Does not run 'clean' action for 'shell', 'chroot', 'install', or
  'installdeps' (docs updated)
- fix build for top_builddir != top_srcdir
- fix 'installdeps' so that it works with both rpms/srpms
- missing device file /dev/ptmx was causing 'expect' command to always
  fail. Affected any SRPM build that used 'expect'.
- hard spec file dep on python >= 2.4 due to python syntax changes.
- resultdir can now contain python-string substitutions for any
  variable in the chroot config.
  rebuild my.src.rpm
- add 'dist' variable to all chroot config files so that it is
  available for resultdir substitutions.
- give good error message when logging.ini cannot be found.
- change default logging format to remove verbosity from build.log.
- make logging format configurable from defaults.cfg or chroot cfg.
- less verbose state.log format

* Mon Oct 22 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.4-1
- fix reported 'bad owner/group' from rpm in some configurations.

* Mon Oct 22 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.3-1
- BZ# 336361 -- cannot su - mockbuild
- BZ# 326561 -- update manpage
- BZ# 235141 -- error with immutable bit

* Sat Oct 20 2007 Michael Brown <mebrown@michaels-house.net> - 0.8.0-1
- huge number of changes upstream
- convert to setuid wrapper instead of old setuid helper
- lots of bugfixes and improvements
- /var/cache/yum now saved and bind-mounted
- ccache integration
- rootcache improvements (formerly called autocache)

* Mon Aug 27 2007 Michael Brown <mebrown@michaels-house.net> - 0.7.6-1
- ensure /etc/hosts is created in chroot properly

* Mon Aug 13 2007 Clark Williams <williams@redhat.com> - 0.7.5-2
- build fix from Roland McGrath to fix compile of selinux lib

* Wed Aug 8 2007 Clark Williams <williams@redhat.com> - 0.7.5-1
- orphanskill feature (BZ#221351)

* Wed Aug 8 2007 Michael Brown <mebrown@michaels-house.net> - 0.7.5-1
- add example configs to defaults.cfg
- dont rebuild cache if not clean build (BZ#250425)

* Wed Jul 18 2007 Michael Brown <mebrown@michaels-house.net> - 0.7.4-1
- return child exit status, so we properly report subcommand failures

* Fri Jul  6 2007 Michael Brown <mebrown@michaels-house.net> - 0.7.3-1
- remove redundant defaults.cfg entries.

* Wed Jun 20 2007 Michael Brown <mebrown@michaels-house.net> - 0.7.2-1
- fix exclude list
- remove legacy configs
- disable 'local' repos by default (koji-repos)

* Wed Jun 13 2007 Michael Brown <mebrown@michaels-house.net> - 0.7.1-1
- Fix problem with autocache where different users couldnt share same cache
- Fix problem creating resolv.conf in rootfs
- cleanup perms on rootfs /etc/

* Tue Jun 12 2007 Michael Brown <mebrown@michaels-house.net> - 0.7.1-1
- add EPEL 5 config files

* Mon Jun 11 2007 Clark Williams <williams@redhat.com> - 0.7-1
- fixed bind mount problems
- added code to allow multiple users to use --no-clean
- merged mock-0-6-branch to head and changed version

* Thu Jun  7 2007 Clark Williams <williams@redhat.com> - 0.6.17-1
- added F-7 config files (BZ#242276)
- modified epel configs for changed mirrorlist location (BZ#239981)
- added bind mount of /dev (BZ#236428)
- added copy of /etc/resolv.conf to chroot (BZ#237663 and BZ#238101)

* Tue May 01 2007 Clark Williams <williams@redhat.com> - 0.6.16-1
- timeout code adds new cmdline option that will kill build process after
  specified timeout. Useful for automated builds of things that may hang during
  build and you just want it to fail.

* Tue Apr 10 2007 Clark Williams <williams@redhat.com> - 0.6.15-1
- Fixed typo in FC4 -epel configs (BZ 235490)

* Sat Feb 24 2007 Clark Williams <williams@redhat.com> - 0.6.14-1
- Ville Skyttä's fix for RPM_OPT_FLAGS (BZ 226673)

* Tue Feb 20 2007 Clark Williams <williams@redhat.com> - 0.6.13-1
- Handle --no-clean option when doing yum.conf symlink (BZ 230824)

* Fri Feb 16 2007 Clark Williams <williams@redhat.com> - 0.6.12-1
- added safety symlink for yum.conf

* Wed Feb  7 2007 Clark Williams <williams@redhat.com> - 0.6.11-1
- added error() calls to print command output on failed commands

* Tue Feb  6 2007 Clark Williams <williams@redhat.com> - 0.6.11-1
- added installdeps command for long-term chroot management

* Mon Jan  8 2007 Clark Williams <williams@redhat.com> - 0.6.10-1
- Added Josh Boyer's EPEL config files

* Tue Nov 21 2006 Clark Williams <williams@redhat.com> - 0.6.9-1
- applied Eric Work's patch to fix defaults vs. command line option problem
  (BZ 215168)
- use /etc/mock/defaults.cfg if --configdir specified and no defaults found
  in the specified configdir
  (BZ 209407)
- applied Jesse Keatings patch for arch specifi config files
  (BZ 213516)

* Mon Oct 30 2006 Clark Williams <williams@redhat.com> - 0.6.8-1
- respun tarballs without buildsys rpms

* Mon Oct 30 2006 Clark Williams <williams@redhat.com> - 0.6.7-1
- updated for FC6 release

* Sat Oct 21 2006 Clark Williams <williams@redhat.com> - 0.6.6-1
- bumped version to 0.6.6 (fixed tarball problem)

* Mon Sep 11 2006 Clark Williams <williams@redhat.com> - 0.6.5-1
- changed version number for patch from Karanbir Singh
  (rpm workaround on CentOS 4.4)

* Tue Aug 29 2006 Clark Williams <williams@redhat.com> - 0.6.3-1
- changed version number to indicate fix for bz 204051

* Tue Aug 29 2006 Clark Williams <williams@redhat.com> - 0.6.2-2
- bumped revision for bz 204051

* Wed Aug 23 2006 Clark Williams <williams@redhat.com> - 0.6.2-1
- Updated README
- Fixed link problem in etc/Makefile
- Bumped version number

* Wed Aug 16 2006 Clark Williams <williams@redhat.com>
- Added buildsys-build specfile to docs
- Added disttag
- Bumped release number

* Wed Jun  7 2006 Seth Vidal <skvidal at linux.duke.edu>
- version update

* Tue Apr 11 2006 Seth Vidal <skvidal at linux.duke.edu>
- specfile version iterate

* Tue Dec 27 2005 Seth Vidal <skvidal@phy.duke.edu>
- add patch from Andreas Thienemann - adds man page

* Sat Jun 11 2005 Seth Vidal <skvidal@phy.duke.edu>
- security fix in mock-helper

* Sun Jun  5 2005 Seth Vidal <skvidal@phy.duke.edu>
- clean up packaging for fedora extras

* Thu May 19 2005 Seth Vidal <skvidal@phy.duke.edu>
- second packaging and backing down the yum ver req

* Sun May 15 2005 Seth Vidal <skvidal@phy.duke.edu>
- first version/packaging
