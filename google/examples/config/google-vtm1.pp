class { 'brocadevtm':
  rest_user   => 'admin',
  rest_pass   => 'Change me, No really, Im on GitHub. I should be the same as startup-script.sh',
  rest_ip     => hiera("googleIP"),
  rest_port   => 9070,
}

brocadevtm::cloud_api_credentials { 'googleScaler':
  ensure                   => present,
  basic__cred1             => 'local',
  basic__cred2             => 'fluted-lambda-122413',
  basic__cred3             => 'europe-west1-b',
  basic__script            => 'googledriver.py',
}

class { 'brocadevtm::global_settings':
  java__enabled                               => true,
}

brocadevtm::persistence { 'webSession':
  ensure              => present,
  basic__cookie       => 'PHPSESSID',
  basic__type         => 'cookie',
}

include brocadevtm::monitors_simple_http

brocadevtm::pools { 'webPool':
  ensure                                   => present,
  basic__monitors                          => '["Simple HTTP"]',
  basic__persistence_class                 => 'webSession',
  auto_scaling__cloud_credentials          => 'googleScaler',
  auto_scaling__enabled                    => true,
  auto_scaling__external                   => false,
  auto_scaling__imageid                    => 'web-image',
  auto_scaling__ips_to_use                 => 'private_ips',
  auto_scaling__min_nodes                  => 1,
  auto_scaling__name                       => 'web',
  auto_scaling__size_id                    => 'n1-standard-1',
  require                                  => [ Class[Brocadevtm::Monitors_simple_http],  Brocadevtm::Persistence['webSession'],  Brocadevtm::Cloud_api_credentials['googleScaler'], ],
}

brocadevtm::virtual_servers { 'webservice':
  ensure                                  => present,
  basic__enabled                          => true,
  basic__pool                             => 'webPool',
  basic__port                             => 80,
  connection__timeout                     => 40,
  web_cache__enabled                      => true,
  require                                 => [ Brocadevtm::Pools['webPool'], ],
}

