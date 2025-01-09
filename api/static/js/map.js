// Posição inicial do mapa em Teresina, PI (Brasil)
var latInicial = -5.0917;  // Latitude de Teresina, PI (Centro da cidade)
var lonInicial = -42.8038;  // Longitude de Teresina, PI (Centro da cidade)
var map = L.map('map').setView([latInicial, lonInicial], 13);

// Adicionar camada do OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Lista estática de apartamentos (com localizações em Teresina)
var apartamentos = [
    {
        nome: "Apartamento Centro",
        descricao: "Apartamento no coração de Teresina, perto de tudo.",
        latitude: -5.0917,   // Centro de Teresina
        longitude: -42.8038
    },
    {
        nome: "Apartamento Zona Leste",
        descricao: "Apartamento em uma das regiões mais dinâmicas de Teresina, com fácil acesso ao comércio.",
        latitude: -5.0700,   // Zona Leste
        longitude: -42.8000
    },
    {
        nome: "Apartamento Zona Sul",
        descricao: "Apartamento amplo e bem localizado na Zona Sul, com várias opções de lazer e compras.",
        latitude: -5.0820,   // Zona Sul
        longitude: -42.7815
    },
    {
        nome: "Apartamento Zona Norte",
        descricao: "Apartamento na Zona Norte, com acesso fácil a importantes avenidas da cidade.",
        latitude: -5.0935,   // Zona Norte
        longitude: -42.7730
    }
];

// Iterar sobre os apartamentos e adicionar marcadores no mapa
apartamentos.forEach(function(apartamento) {
    // Verificar se latitude e longitude são válidas
    var lat = apartamento.latitude || latInicial;
    var lon = apartamento.longitude || lonInicial;
    
    // Adicionar marcador no mapa
    L.marker([lat, lon]).addTo(map)
        .bindPopup("<b>" + apartamento.nome + "</b><br>" + apartamento.descricao + "")
        .openPopup();
});
