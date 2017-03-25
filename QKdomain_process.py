#! /usr/bin/python

"""
%prog fasta interproscan_output abbreviations process_summary
Reads InterProScan output and user-defined abbreviations, performs the following analyses:
	1. Defines the non-overlapping domain structure
	2. Exports individual or multiple sequential domains (NB, NB-LRR, CC-NB)
	3. Permits extended domain export (+/- based on length of domain or fixed values)

Author: Matthew Moscou <matthew.moscou@tsl.ac.uk>
"""

# modules
import optparse
from optparse import OptionParser
import sets
import string


# import arguments and options
usage = "usage: %prog fasta interproscan_output abbreviations process_summary [selected_domain_output]"
parser = OptionParser(usage=usage)
parser.add_option("-d", "--domain", action="store", type="string", dest="domain", default="", help="Individual domain(s) to export")
parser.add_option("-n", "--nextend", action="store", type="float", dest="nextend", default=-1, help="Extended N-terminal export for selected domain")
parser.add_option("-c", "--cextend", action="store", type="float", dest="cextend", default=-1, help="Extended C-terminal export for selected domain")
parser.add_option("-u", "--undefined", action="store", dest="undefined", default="", help="Export undefined regions (i.e. without annotation)")
(options, args) = parser.parse_args()


# import protein sequence (FASTA)
fasta_file = open(args[0], 'r')
	
ID_sequence = {}
	
for line in fasta_file.readlines():
	if len(line) > 0:
		if line[0] == '>':
			ID = string.split(line)[0][1:]
			ID_sequence[ID] = ''
		else:
			ID_sequence[ID] += string.split(line)[0]
	
fasta_file.close()
	

# import domain abbreviations
domain_abbreviation = {}
domain_group_identifiers = {}

abbreviation_file = open(args[2], 'r')

for line in abbreviation_file.readlines():
	line = string.replace(line, '\n', '')
	sline = string.split(line, '\t')

	if len(sline) > 1:
		domain_abbreviation[sline[0]] = sline[1]

		if sline[1] not in domain_group_identifiers.keys():
			domain_group_identifiers[sline[1]] = []
	
		domain_group_identifiers[sline[1]].append(sline[0])

abbreviation_file.close()


# initialize gene position domain dictionary
gene_position_domain = {}
	
for gene in ID_sequence.keys():
	gene_position_domain[gene] = []

	for index in range(len(ID_sequence[gene])):
		gene_position_domain[gene].append([])


# interproscan analysis
interproscan_file = open(args[1], 'r')
	
interproscan_data = interproscan_file.readlines()

gene_domains = [0]
geneID = string.split(interproscan_data[0])[0]
	
for line in interproscan_data:
	sline = string.split(line, '\t')
	
	for position_index in range(int(sline[6]) - 1, int(sline[7])):
		if sline[4] in domain_abbreviation.keys():
			gene_position_domain[sline[0]][position_index].append(domain_abbreviation[sline[4]])
	
interproscan_file.close()

# domain analysis
process_summary_file = open(args[3], 'w')

if len(args) > 4:
	individual_domain_file = open(args[4], 'w')

if len(options.undefined) > 0:
	undefined_region_file = open(options.undefined, 'w')

for gene in gene_position_domain.keys():
	gene_structure = []
	gene_structure_start_stop = []

	positions = range(len(gene_position_domain[gene]))
	local_domains = []
	start = -1

	# if undefined, initialize start position
	if len(options.undefined) > 0:
		if len(gene_position_domain[gene][0]) == 0:
			undefined_start = 0
		else:
			undefined_start = -1

		undefined_domain_index = 1

	for position in positions:
		# if position contains one or more domains
		if len(gene_position_domain[gene][position]) > 0:
			# add domains to local_domains
			for domain in gene_position_domain[gene][position]:
				local_domains.append(domain)

			# initialize start of domain if first instance
			if start < 0:
				start = position
	
			# if undefined was active, export position between domains, reset undefined
			if len(options.undefined) > 0:
				if undefined_start >= 0:
					undefined_region_file.write('>'  + gene + '_' + str(undefined_domain_index) + '_' + str(undefined_start) + '_' + str(position) + '\n')
					undefined_region_file.write(ID_sequence[gene][undefined_start:position] + '\n')

					undefined_start = -1
					undefined_domain_index += 1
		
		# if position does not contain a domain
		elif len(gene_position_domain[gene][position]) == 0:
			# add domain(s) to gene structure that ended, reinitialize
			if len(local_domains) > 0:
				for domain_group in domain_group_identifiers.keys():
					if len(sets.Set(local_domains) & sets.Set([domain_group])) > 0:
						gene_structure.append(domain_group)
						gene_structure_start_stop.append([start, position])
				
				start = -1

				local_domains = []

			# if undefined, initialize start position
			if len(options.undefined) > 0:
				if undefined_start < 0:
					undefined_start = position

	# at end of sequence, if domains reach end, add domain(s) to gene structure
	if len(local_domains) > 0:
		for domain_group in domain_group_identifiers.keys():
			if len(sets.Set(local_domains) & sets.Set(domain_group_identifiers[domain_group])) > 0:
				gene_structure.append(domain_group)
				gene_structure_start_stop.append([start, position])
	
	# export ordered domain structure
	process_summary_file.write(gene + '\t' + '-'.join(gene_structure) + '\n')

	# if exporting specific domain(s), scan for multiple structures in protein sequence
	if len(options.domain) > 0:
		num_domains = options.domain.count('-') + 1

		for index in range(0, len(gene_structure) - num_domains + 1):
			if options.domain == '-'.join(gene_structure[index:(index+num_domains)]):
				if options.nextend > 0:
					if options.nextend >= 1.0:
						if (gene_structure_start_stop[index][0] - int(options.nextend)) >= 0:
							local_start = gene_structure_start_stop[index][0] - int(options.nextend)
						else:
							local_start = 0
					else:
						if (gene_structure_start_stop[index][0] - (options.nextend * (gene_structure_start_stop[index + num_domains - 1][1] - gene_structure_start_stop[index][0]))) >= 0:
							local_start = gene_structure_start_stop[index][0] - int(options.nextend * (gene_structure_start_stop[index + num_domains - 1][1] - gene_structure_start_stop[index][0]))
						else:
							local_start = 0

				else:
					local_start = gene_structure_start_stop[index][0]

				if options.cextend > 0:
					if options.nextend >= 1.0:
						if (gene_structure_start_stop[index + num_domains - 1][1] + int(options.cextend)) < len(ID_sequence[gene]):
							local_stop = gene_structure_start_stop[index + num_domains - 1][1] + int(options.cextend)
						else:
							local_stop = len(ID_sequence[gene])
					else:
						if (gene_structure_start_stop[index + num_domains - 1][1] + (options.cextend * (gene_structure_start_stop[index + num_domains - 1][1] - gene_structure_start_stop[index][0]))) < len(ID_sequence[gene]):
							local_stop = gene_structure_start_stop[index + num_domains - 1][1] + int(options.cextend * (gene_structure_start_stop[index + num_domains - 1][1] - gene_structure_start_stop[index][0]))
						else:
							local_stop = len(ID_sequence[gene])
				else:
					local_stop = gene_structure_start_stop[index + num_domains - 1][1]

				if len(args) > 4:
					individual_domain_file.write('>' + gene + '_' + str(local_start) + '_' + str(local_stop) + ' ' + '-'.join(gene_structure) + '\n')
					individual_domain_file.write(ID_sequence[gene][local_start:local_stop] + '\n')

process_summary_file.close()

if len(args) > 4:
	individual_domain_file.close()

if len(options.undefined) > 0:
	undefined_region_file.close()
