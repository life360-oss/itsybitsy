`# V1

* [x] output the graph basic
* [x] graph output prettier
* [x] combine http and https backends
* [x] add --max-depth
* [x] detect service name from /etc/chef/client.rb
* [x] add nsq graph
* [x] add --skip-nsq-topics
* [x] detect defunct children via haproxy stats
* [x] skip display defunct children
* [x] haproxy 1.6 and 1.8 compatability
* [x] add error state for "null" NSQ clients (use "?")
* [x] detect missing stats socket haproxy
* [x] task: validate missing haproxy stats socket config is live manually with knife ssh
* [x] task: validate missing haproxy stats socket is live manually with knife ssh
* [x] add "no consumer" NSQ detection
* [x] task: validate DEFUNCT-ness
* [x] multiple seeds

# V2.async
* [x] use asyncssh (10x faster!)
* [x] remove `return_exceptions=True`
* [x] use global BASTION connection (https://github.com/ronf/asyncssh/issues/270)
* [x] limit concurrency w/ semaphore
* [x] split to modules
* [x] re-use ssh connection for get-name/get-config calls
* [x] pass lightweight node-ref through async calls instead of node dict
* [x] remove pending node print
* [x] deal with formatting/output-ordering implications
* [x] convert recursive crawl from `await` to `ensure_future`
* [x] improve live output rendering
* [x] fix introduced parent['last_sibling'] bug
* [x] bug: cycle is correct in the tree, but rendering zombie children (only for first level cycles?)
* [x] retry ssh connection 3 times, fine tune concurrency
* [x] introduced: --output=stdout is now broken due to render_node_live
* [x] rename water to water_spout, private module function
* [x] consolidate `find..children` error checking
* [x] validate frontend-router
* [x] move connection semaphore to ssh_layer
* [x] better trace/debug log levels
* [x] consolidate nsq node relationships w/ multiple connections
* [x] deal w/ SSH config: bastion & username
* [x] refactors from PR review (reduce complexity, procedural styling)

# V2.features
* [x] DISPLAY: output in json
* [x] DISPLAY: load json file
* [x] DISPLAY: output in graphviz
* [x] DISPLAY: graphviz source
* [x] CRAWL: detect proxysql
* [x] CRAWL: cassandra
* [x] CRAWL: detect well known ports w/ netstat & AWS name lookup (cx, memcache, redis)
* [x] CRAWL: detect postgres well known port - causing trouble w/ name lookup
* [x] CRAWL: user defined links
* [x] move hints/skips to web.yaml
* [x] keep config.yaml
* [x] CRAWL: kinesis

# V2.refactor
* [x] move grouping of nsq topics to application layer, on service_name instead of IP
* [x] `config_errors` -> `warnings`, `crawl_errors` -> `errors`
* [x] refactor ssh config to ssh config file
* [x] refactor --hide-defunct to --skip-defunct and do not even (crawl)
* [x] graphviz warn/error color coding
* [x] remove "cruft" handling
* [x] add quick filter to rewrite service_name mysql-main-port_3306 to mysql-main-r/o
* [x] create objects or named tuples (dataclasses!)
* [x] PEP8, 120 line length 
* [x] CHARLOTTE: make the `get_config` function into configurable parsers definable in YAML
* [x] charlotte: replace 'null' response from NSQ for missing IP w/ actual None response
* [x] charlotte: move crawl strategy exceptions (frontend-router) into charlotte
* [x] charlotte: move blocking logic to charlotte
* [x] charlotte: rename crawl_strategy -> crawl_provider on Node()
* [x] charlotte: move service_name_rewrite to charlotte
* [x] rename protocol_detail -> protocol_mux
* [x] CHARLOTTE: --skip-{name} arguments
* [x] --skip-defunct -> --hide-defunct
* [x] refactor database named matching to port matching
* [x] move skip services from globals to argparse
* [x] move crawl_complete, name_lookup_complete to node.py
* [x] charlotte config 1 file to directory of yaml files
* [x] create default yaml file for argparse
* [x] rename `ip` -> `instance_address`
* [x] remove crawl strategy object from Node, denormalize (protocol, blocking)
* [x] merge hints into pre-existing children w/ unknown address
* [x] CORE: add sub commands for ['crawl', 'render-json']
* [x] CORE (OSS): unit tests tests tests (round I - excluding `provider_*.py` and `crawl.py`)


# V2.bugs
* [x] BUG: nsq channels on same node are not grouping, again!
* [x] there is a regression in cycle detection - spider against async-cake-handler to repro
* [x] trim double quotes from service_name
* [x] BUG: crawl of well known port is discovering random connections to frontend-routers, ELBs  - fixed by chris r. source ephemeral port filter
* [x] `'CYCLE': f"service '{node['service_name']}' discovered as a parent of itself!",`
* [x] paramiko nested exception outputting
* [x] handle actually null (absent value) nsq consumer in additionn to string literal "null"
* [x] ascii renderer grouping by detail is persisting in memory (groupings)
* [x] charlotte: move name parser expections (mysql-main) into charlotte
* [x] we see many repeating group by service-name NSQ topic/channels repeating in ascii renderer
* [x] catch timeout for crawling children
* [x] remove trailing `_` from node_ref
* [x] graphviz blocking is backwards
* [x] regression defunct in parser check on num_connections == 0 is failing
* [x] differentiate RDS databases found in AWS - currently all show as `rdsnetworkinterface`
* [x] BUG: add __type__ to json serialization - currently brittle: key-ing off of random fields for deserialization
* [x] infinited recursion bug introduced by the crawl hints.  it had to do with the cached_nodes in crawl.py being by_ref object and a deep-ish copy fixed
* [x] trying to crawl json that was outputted with --depth arg results in hanging `wait_for_crawl` to complete on nodes

# V3 Kubernetes++
* [x] CRAWL: kubernetes - take a hint
* [x] CRAWL: kubernetes - name lookup, crawl
* [x] support EKS cluster in a different AWS account than provider_aws
 

# V3.refactor
* [x] static code analysis (prospector) and forthcoming changes
* [x] refactor providers to objects, remove SSH logic from crawl.py
* [x] caching children in crawl.py instead of providers!!
* [x] fix TIMEOUT logic
* [x] put provider_args back in crawl strategies! use **kwargs to pass args in code
* [x] rewrite provider registration
* [x] move provider constant refs from constants.py into providers
* [x] rename errors.NULL_IP NULL_ADDRESS
* [x] refactor signature of `crawl_downstream` to include address
* [x] replace pass through node_ref in crawl w/ `zip()`
* [x] unit tests for crawl, providers, provider_*?
* [x] validate that crawl strategies are only used for specified providers
* [x] refactor lookup_name to remove life360 business logic from providers!
* [x] remove ProviderInterface::configure(), have ssh configure itself on first query
* [x] seed provider is configurable command line arg w/

# V3.features
* [x] FEATURE: make instance_provider args for aws hints part of a refactored "profile"
* [x] FEATURE: Distinguish kubernetes service shape in graphviz
* [ ] add --stop-on-nonblocking CLI arg

# V3.bugs
* [x] not respecting CrawlStrategy.providers
* [x] need to be able to configure different AWS profile for k8s/eks than for aws! (for dev)
* [x] BUG: intermittent timeout exceptions which do not result in program exit

# V4.VOSS
* [x] REFACTOR: (providers): providers as plugin architecture
* [x] REFACTOR (spider): --concurrency -> --ssh-concurrency OR provider args
* [x] REFACTOR: (all): refactor package architecture
* [x] TIMEOUT: (crawl) robust provider timeout and exception handling
* [x] OBSCURIFIER (render_*): obscurifier for output
* [x] BUG: fix namespace package not being include in dist

# V5.PROMVIZ
* [~] promviz render output
  * [x] render nsq
  * [x] haproxy http enabled in prod
  * [x] render haproxy
  * [x] render proxysql
  * [x] BUG: geonames orphaned due to no data returned query
  * [x] render haproxy tcp mode
  * [ ] render elasticache
  * [ ] render kinesis
  * [ ] render custom queries
* [x] merge hints
* [x] add missing hints
* [x] render_promviz tests
* [x] refactor renderers to plugins
* [x] fix plugin imports
* [x] refactor/DRY providers/renderes to plugin_core.py
* [x] how to organize plugin tests?
* [ ] move constants.ARGS to cli_args.ARGS
* [ ] update examples plugins/crawl strategies/docs
* [~] PLUGINS: BUG namespace plugins aren't pip install --editable-able

# V5.1 NICETOHAVES
* [ ] ci/cd run tests
* [ ] ci/cd publish pypy package
* [ ] annotate services w/ links to wiki/github

# Backlog

## New Features

## Core
* [ ] RENDER_PLUGINS: make renderer's an abstract class w/ plugins
* [ ] REFACTOR: move seed logic out of ./spider.py
* [ ] REFACTOR: revisit the Node{Protocol, CrawlStrategy, protocol_mux} object relationship strategy
* [ ] FEATURE: track whether a node was skipped for crawling and display as such in graphviz
* [ ] REFACTOR: move errors/warnings to a global config
* [ ] REFACTOR: do not block crawl() on lookup_name() in main crawl loop.  will speed up many times
* [ ] REFACTOR: move mutex from provider_ssh to crawl.py
* [ ] BUG: intermittent timeouts crawling the whole tree - add retry to lookup_name/crawl_downstream?
* [ ] BUG: remove `blocking` from CrawlStrategy - it should only be in Protocol
* [ ] BUG: where is `elasticache-time-points`? crawl-netstat only takes 1 ip per port, so for async-soa which has 2 downstreams on 6379, it can't find
* [ ] BUG: where is `cx-dvb`?? 
* [ ] REFACTOR: consolidate Node::crawl_complete and crawl.py::_crawlable()
* [ ] BUG: required args showing as optional in --help
* [ ] DOCS: remove non obfuscated example video from README
* [ ] LOGGER: rewrite logger access for community standards
* [ ] PLUGPLAY: out of the box functionality by moving TCP to a "builtin" CrawlStrategy and using `hostname` or default service name
* [ ] REFACTOR: (providers): rewrite take_a_hint to not return a list, just return a single NodeTransport
* [ ] DOCS: rewrite docs in sphinx style and prepare for export to readthedocs.org
* [ ] FEATURE: a new render format that has a predictable sort order, and on top of that the ability to diff

## Renderers
* test coverage for renderers.py

## Remder Ascii
* [ ] FEATURE: merge hints in ascii output

## Render Graphviz
* [ ] FEATURE: multiple seeds display with equal ranking
* [ ] FEATURE: nsq topics as nodes rather than edges
* [ ] FEATURE: visualize cycles
* [ ] FEATURE: different visualization for cache vs database
* [ ] FEATURE: create a legend

## Render JSON

## Render New
* [ ] DISPLAY: output in vizceral format
* [ ] DISPLAY: 'diff' run on multiple seed nodes and diff!

## CrawlStrategies
* [ ] BUG: HAProxy: functionality to detect bad HAProxy Config as a crawl error was lost in async refactor  `if stdout.startswith('ERROR:'): return 'CRAWL ' + stdout.replace("\n","\t"), {}`
* [ ] BUG: NSQ: misconfigured clients have null server (this is why we don't see rattail -> relapse), investigate & resolve
* [ ] FEATURE: Netstat: use matchAddress for HAProxy crawl strategies to avoid timeout to RDS hostnames
* [ ] FEATURE: crawl downstream - ability to specify more providers args per provider (so that k8s can selectively crawl containers)
* [ ] FEATURE: detect multiple downstream on same port with NetstatCrawlStrategy - it will only pick up the first

## Providers
* [ ] BUG: cli arg --disable-providers is broken


## Provider SSH
* [ ] FEATURE: revisit whether `occupy_one_sempahore_space` is working (to dynamically configure --concurrency) 
* [ ] FEATURE: still getting ssh connections errors sometimes with out --concurrency=10
* [ ] FEATURE: configurable "~/.ssh/config" SSH profile
* [ ] REFACTOR (provider_ssh): we shouldn't use known_hosts=None for security reasons
* [ ] TEST: write tests for provider_ssh

## Provider AWS
* [ ] FEATURE: lookup_name is slow, use async
* [ ] CRAWL: dynamodb
* [ ] CRAWL: SQS
* [ ] TEST: write tests for provider_aws

## Provider K8S
* [ ] TEST: write tests for provider_k8s

## Charlotte
* [ ] FEATURE (charlotte): yaml validation by schema

## Web

# Trash Can
* [ ] backwards compatability for haproxy w/out stats socket
* [ ] detect live traffic netstat/tcpdump/ebpf? (this was solved by using haproxy stats)
* [ ] remove crawl_strategy from Node()
