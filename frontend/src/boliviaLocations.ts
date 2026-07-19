// Catálogo territorial basado en el Anexo 3 del INE para el Censo 2024.
const RAW_MUNICIPALITIES: Record<string, string> = {
  Chuquisaca:
    "Sucre|Yotala|Poroma|Azurduy|Tarvita|Zudáñez|Presto|Mojocoya|Icla|Padilla|Tomina|Sopachuy|Alcalá|El Villar|Monteagudo|Huacareta|Tarabuco|Yamparáez|Camargo|San Lucas|Incahuasi|Villa Charcas|Villa Serrano|Villa Abecia|Culpina|Las Carreras|Villa Vaca Guzmán|Huacaya|Macharetí",
  "La Paz":
    "La Paz|Palca|Mecapaca|Achocalla|El Alto|Achacachi|Ancoraimes|Huarina|Santiago de Huata|Huatajata|Chua Cocani|Corocoro|Caquiaviri|Calacoto|Comanche|Charaña|Waldo Ballivián|Nazacara de Pacajes|Santiago de Callapa|Puerto Acosta|Mocomoco|Puerto Carabuco|Humanata|Escoma|Chuma|Ayata|Aucapata|Sorata|Guanay|Tacacoma|Quiabaya|Combaya|Tipuani|Mapiri|Teoponte|Apolo|Pelechuco|Viacha|Guaqui|Tiahuanacu|Desaguadero|San Andrés de Machaca|Jesús de Machaca|Taraco|Luribay|Sapahaqui|Yaco|Malla|Cairoma|Inquisivi|Quime|Cajuata|Colquiri|Ichoca|Villa Libertad Licoma|Chulumani|Irupana|Yanacachi|Palos Blancos|La Asunta|Pucarani|Laja|Batallas|Puerto Pérez|Sica Sica|Umala|Ayo Ayo|Calamarca|Patacamaya|Colquencha|Collana|Coroico|Coripata|Ixiamas|San Buenaventura|Charazani|Curva|Copacabana|San Pedro de Tiquina|Tito Yupanqui|San Pedro de Curahuara|Papel Pampa|Chacarilla|Santiago de Machaca|Catacora|Caranavi|Alto Beni",
  Cochabamba:
    "Cochabamba|Aiquile|Pasorapa|Omereque|Independencia|Morochata|Cocapata|Tarata|Anzaldo|Arbieto|Sacabamba|Arani|Vacas|Arque|Tacopaya|Capinota|Santiváñez|Sicaya|Cliza|Toco|Tolata|Quillacollo|Sipe Sipe|Tiquipaya|Vinto|Colcapirhua|Sacaba|Colomi|Villa Tunari|Tapacarí|Totora|Pojo|Pocona|Chimoré|Puerto Villarroel|Entre Ríos|Mizque|Vila Vila|Alalay|Raqaypampa|Punata|Villa Rivero|San Benito|Tacachi|Villa Gualberto Villarroel|Bolívar|Tiraque|Shinahota",
  Oruro:
    "Oruro|Caracollo|El Choro|Paria|Challapata|Santuario de Quillacas|Corque|Choquecota|Curahuara de Carangas|Turco|Huachacalla|Escara|Cruz de Machacamarca|Yunguyo del Litoral|Esmeralda|Poopó|Pazña|Antequera|Huanuni|Machacamarca|Salinas de Garci Mendoza|Pampa Aullagas|Sabaya|Coipasa|Chipaya|Toledo|Eucaliptus|Santiago de Andamarca|Belén de Andamarca|San Pedro de Totora|Santiago de Huari|La Rivera|Todos Santos|Carangas|Santiago de Huayllamarca",
  Potosí:
    "Potosí|Tinguipaya|Yocalla|Urmiri|Uncía|Chayanta|Llallagua|Chuquihuta Ayllu Jucumani|Betanzos|Chaquí|Tacobamba|Colquechaca|Ravelo|Pocoata|Ocurí|San Pedro de Macha|San Pedro de Buena Vista|Toro Toro|Cotagaita|Vitichi|Sacaca|Caripuyo|Tupiza|Atocha|Colcha K|San Pedro de Quemes|San Pablo de Lípez|Mojinete|San Antonio de Esmoruco|Puna|Caiza D|Ckochas|Uyuni|Tomave|Porco|Jatun Ayllu Yura|Arampampa|Acasio|Llica|Tahua|Villazón|San Agustín",
  Tarija:
    "Tarija|Padcaya|Bermejo|Yacuiba|Caraparí|Villa Montes|Uriondo|Yunchará|San Lorenzo|El Puente|Entre Ríos",
  "Santa Cruz":
    "Santa Cruz de la Sierra|Cotoca|Porongo|La Guardia|El Torno|Warnes|Okinawa Uno|San Ignacio de Velasco|San Miguel de Velasco|San Rafael|Buena Vista|San Carlos|Yapacaní|San Juan de Yapacaní|San José de Chiquitos|Pailón|Roboré|Portachuelo|Santa Rosa del Sara|Colpa Bélgica|Lagunillas|Charagua Iyambae|Cabezas|Cuevo|Kereimba Iyaambae|Camiri|Boyuibe|Vallegrande|El Trigal|Moro Moro|Postrervalle|Pucará|Samaipata|Pampa Grande|Mairana|Quirusillas|Montero|General Saavedra|Mineros|Fernández Alonso|San Pedro|Concepción|San Javier|San Julián|San Antonio de Lomerío|San Ramón|Cuatro Cañadas|San Matías|Comarapa|Saipina|Puerto Suárez|Puerto Quijarro|Carmen Rivero Tórrez|Ascensión de Guarayos|Urubichá|El Puente",
  Beni:
    "Trinidad|San Javier|Riberalta|Guayaramerín|Reyes|San Borja|Santa Rosa del Yacuma|Rurrenabaque|Santa Ana del Yacuma|Exaltación|San Ignacio de Moxos|Loreto|San Andrés|San Joaquín|San Ramón|Puerto Siles|Magdalena|Baures|Huacaraje|Territorio Indígena Multiétnico TIM",
  Pando:
    "Cobija|Porvenir|Bolpebra|Bella Flor|Puerto Rico|San Pedro|Filadelfia|Puerto Gonzalo Moreno|San Lorenzo|El Sena|Santa Rosa del Abuná|Ingavi|Nueva Esperanza|Villa Nueva|Santos Mercado",
};

export const BOLIVIA_DEPARTMENTS = Object.keys(RAW_MUNICIPALITIES);

export const BOLIVIA_MUNICIPALITIES: Record<string, string[]> = Object.fromEntries(
  Object.entries(RAW_MUNICIPALITIES).map(([department, values]) => [
    department,
    values.split("|"),
  ]),
);

export function municipalitiesFor(department: string) {
  return BOLIVIA_MUNICIPALITIES[department] ?? [];
}
