# 
# Do NOT Edit the Auto-generated Part!
# Generated by: spectacle version 0.27
# 

Name:       systemdatascope

# >> macros
# << macros

%{!?qtc_qmake:%define qtc_qmake %qmake}
%{!?qtc_qmake5:%define qtc_qmake5 %qmake5}
%{!?qtc_make:%define qtc_make make}
%{?qtc_builddir:%define _builddir %qtc_builddir}
Summary:    System Data Scope
Version:    0.5.0
Release:    1
Group:      Qt/Qt
License:    MIT
URL:        https://github.com/rinigus/systemdatascope
Source0:    %{name}-%{version}.tar.bz2
Source100:  systemdatascope.yaml

Requires:   sailfishsilica-qt5 >= 0.10.9
Requires:   rrdtool
Requires:   collectd, collectd-python
Requires:   python(abi) > 3.0
Requires:   python3-dbus

BuildRequires:  pkgconfig(sailfishapp) >= 1.0.2
BuildRequires:  pkgconfig(Qt5Core)
BuildRequires:  pkgconfig(Qt5Qml)
BuildRequires:  pkgconfig(Qt5Quick)
BuildRequires:  desktop-file-utils

%description
SystemDataScope is a GUI for visualization of collectd
datasets. Together with collectd and RRDtool, it provides a system
monitoring solution for Sailfish.

PackageName: SystemDataScope
Type: desktop-application
Custom:
  Repo: https://github.com/rinigus/systemdatascope
Categories:
  - System
  - Utility
Icon: https://raw.githubusercontent.com/rinigus/systemdatascope/master/icons/systemdatascope.svg
Screenshots:
  - https://raw.githubusercontent.com/rinigus/systemdatascope/master/screenshots/sailfish-overall.png
  - https://raw.githubusercontent.com/rinigus/systemdatascope/master/screenshots/sailfish-load-details.png
Url:
  Donation: https://rinigus.github.io/donate

%prep
%setup -q -n %{name}-%{version}

# >> setup
(cd qml && ln -s Platform.silica Platform) || true
# << setup

%build
# >> build pre
# << build pre

%qtc_qmake5  \
    VERSION='%{version}-%{release}'

%qtc_make %{?_smp_mflags}

# >> build post
# << build post

%install
rm -rf %{buildroot}
# >> install pre
# << install pre
%qmake5_install

# >> install post
chmod 755 %{buildroot}%{_bindir}/systemdatascope-makeconfig
# << install post

desktop-file-install --delete-original       \
  --dir %{buildroot}%{_datadir}/applications             \
   %{buildroot}%{_datadir}/applications/*.desktop

%files
%defattr(-,root,root,-)
%{_bindir}
%{_datadir}/%{name}
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/*/apps/%{name}.png
# >> files
# << files
