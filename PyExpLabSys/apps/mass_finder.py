import math
from itertools import product

elements = {}

elements['H'] = {}
elements['H']['isotopes'] = [(0.999885, 0.999885),
                             (0.000115, 2.0141017778)]

elements['C'] = {}
elements['C']['isotopes'] = [(0.9893, 12.0),
                             (0.0107, 13.0033548378)]

elements['O'] = {}
elements['O']['isotopes'] = [(0.99757, 15.99491461956),
                             (0.00038, 16.99913170),
                             (0.00205, 17.9991610)]

elements['Al'] = {}
elements['Al']['isotopes'] = [(1, 26.9815386)]

elements['Cl'] = {}
elements['Cl']['isotopes'] = [(0.7576, 34.96885268),
                              (0.2424, 36.96590259)]

elements['S'] = {}
elements['S']['isotopes'] = [(0.9493, 31.97207100),
                             (0.0076, 32.97145876),
                             (0.0429, 33.96786690),
                             (0.0002, 35.96708076)]


class MassCalculator(object):

    def __init__(self, elements):
        self.elements = elements

    def isotope_spectrum(self, element_list):
        """ Calculate isotope spectrum of molecule """
        spectrum = []
        index_list = []
        for element in element_list:
             index_list.append(range(0, len(self.elements[element]['isotopes'])))

        for index in product(*index_list):
            propability = 1
            mass = 0
            for i in range(0, len(element_list)):
                current_isotope = self.elements[element_list[i]]['isotopes'][index[i]]
                propability *= current_isotope[0]
                mass += current_isotope[1]
            spectrum.append((propability, mass))
        return spectrum

    def elemental_combinations(self, target_mass, element_list=None):
        """ Find all molecular combination with a highest peak close
        to target mass """
        max_amounts = {}
        for element in self.elements:
            # This currently assumes most abundant element is first in list
            weight = self.elements[element]['isotopes'][0][1]
            amount = int(math.floor(target_mass/weight))
            if amount > 0:
                max_amounts[element] = amount

        range_lists = []
        element_list = []
        for element in max_amounts:
            range_lists.append(range(0, max_amounts[element]+1))
            element_list.append(element)

        candidates = []
        for index in product(*range_lists):
            weight = 0
            for i in range(0, len(element_list)):
                element_weight = index[i] * self.elements[element_list[i]]['isotopes'][0][1]
                weight += element_weight

            if (weight > target_mass - 0.5) and (weight < target_mass + 0.5):
                candidate = {}
                for i in range(0, len(element_list)):
                    if index[i] > 0:
                        candidate[element_list[i]] = index[i]
                candidates.append(candidate)
        return candidates


ms = MassCalculator(elements)

#print ms.isotope_spectrum(['C', 'O', 'Cl'])

print(ms.elemental_combinations(85))

