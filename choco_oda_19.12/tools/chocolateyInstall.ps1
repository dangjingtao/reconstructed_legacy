Install-ChocolateyPackage `
  -PackageName "$env:ChocolateyPackageName" `
  -FileType 'MSI' `
  -SilentArgs '/QN' `
  -Url "https://download.opendesign.com/guestfiles/ODAFileConverter/ODAFileConverter_QT5_vc10dll.msi" `
  -Checksum 'a56fff931f5eb58d0e675ebca4269696fa156c4da1859672e41745808ca557e6' `
  -ChecksumType 'SHA256' `
  -Url64bit 'https://download.opendesign.com/guestfiles/ODAFileConverter/ODAFileConverter_QT5_vc14_amd64dll.msi' `
  -Checksum64 '7685c87e964a4e74a3b87b96806d91e4779e3124d32683c10e10a76955823045' `
  -ChecksumType64 'SHA256'
