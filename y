api:
  base_url: https://uk-employment-law-change-detector.onrender.com
  timeout: 30
schedule:
  frequency: weekly
  day: tuesday
  time: 08:00
acts:
- name: Employment Rights Act 1996
  url: https://www.legislation.gov.uk/ukpga/1996/18
notifications:
  email:
    enabled: true
    smtp_host: smtp.gmail.com
    smtp_port: 587
    use_tls: true
    username: engrstephdez@gmail.com
    password: '#Only1God'
    from_addr: engrstephdez@gmail.com
    to_addrs:
    - engrstephdez@gmail.com
  slack:
    enabled: false
    webhook_url: ''
  webhook:
    enabled: false
    url: ''
    method: POST
    headers:
      Content-Type: application/json
