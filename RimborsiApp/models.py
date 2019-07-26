import datetime
import os

from codicefiscale import codicefiscale
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

MEZZO_CHOICES = (
    ("AUTO", "Auto"),
    ("AEREO", "Aereo"),
    ("TRENO", "Treno"),
    ("BUS", "Bus"),
)

MOTIVAZIONE_AUTO_CHOICES = (
    ("Convenienza economica", "Convenienza economica (da dimostrare)"),
    ("Destinazione non servita da mezzi pubblici", "Destinazione non servita da mezzi pubblici"),
    ("Servizio pubblico particolarmente disagiato", "Servizio pubblico particolarmente disagiato"),
    ("Orari inconciliabili con i tempi della missione", "Orari inconciliabili con i tempi della missione"),
    ("Trasporto di materiali e/o strumenti", "Trasporto di materiali e/o strumenti"),
    ("Orari inconciliabili con necessità di rientro in sede", "Orari inconciliabili con necessità di rientro in sede"),
    # (7, "Vuoto"),
)


class Automobile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    marca = models.CharField(max_length=50)
    modello = models.CharField(max_length=100)
    targa = models.CharField(max_length=8)

    def __str__(self):
        return self.marca + ' ' + self.modello + ' ' + self.targa

    class Meta:
        verbose_name_plural = "Automobili"


class Categoria(models.Model):
    nome = models.CharField(max_length=1)
    massimale_docenti = models.FloatField()
    massimale_tecnici = models.FloatField()

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Categorie"


class Stato(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Stati"


class Missione(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    citta_destinazione = models.CharField(max_length=100)
    stato_destinazione = models.ForeignKey(Stato, on_delete=models.SET_NULL, null=True)
    inizio = models.DateField()
    inizio_ora = models.TimeField()
    fine = models.DateField()
    fine_ora = models.TimeField()
    fondo = models.CharField(max_length=100)
    motivazione = models.CharField(max_length=100, null=True, blank=True)
    struttura_fondi = models.CharField(max_length=200)
    automobile = models.ForeignKey(Automobile, null=True, blank=True, on_delete=models.SET_NULL)
    scontrino = models.TextField(null=True, blank=True)
    pernottamento = models.TextField(null=True, blank=True)
    convegno = models.TextField(null=True, blank=True)
    altrespese = models.TextField(null=True, blank=True)

    mezzi_previsti = models.CharField(max_length=100, null=True, blank=True)
    motivazione_automobile = models.CharField(max_length=200, null=True, blank=True)

    @property
    def durata_gg(self):
        return self.fine - self.inizio + datetime.timedelta(days=1)

    @property
    def data_richiesta(self):
        if datetime.date.today() < self.inizio:
            return datetime.date.today()
        else:
            return self.inizio - datetime.timedelta(days=1)

    class Meta:
        verbose_name_plural = "Missioni"

    def __str__(self):
        return f'{self.inizio} - {self.stato_destinazione} - {self.citta_destinazione}'


class Trasporto(models.Model):
    missione = models.ForeignKey(Missione, on_delete=models.CASCADE)
    data = models.DateField()
    da = models.CharField(max_length=100)
    a = models.CharField(max_length=100)
    mezzo = models.CharField(max_length=5, choices=MEZZO_CHOICES)
    tipo_costo = models.CharField(max_length=50)
    costo = models.FloatField()
    km = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Trasporti"


class Indirizzo(models.Model):
    via = models.CharField(max_length=100)
    n = models.CharField(max_length=20)
    comune = models.ForeignKey('comuni_italiani.Comune', on_delete=models.PROTECT, null=True)
    provincia = models.ForeignKey('comuni_italiani.Provincia', on_delete=models.PROTECT, null=True)

    def __str__(self):
        return f'{self.via} {self.n}, {self.comune.name}, {self.provincia.name} ({self.provincia.codice_targa})'

    class Meta:
        verbose_name_plural = "Indirizzi"


class Profile(models.Model):
    QUALIFICA_CHOICES = (
        ('DOTTORANDO', 'Dottorando'),
        ('ASSEGNISTA', 'Assegnista'),
        ('STUDENTE', 'Studente'),
        ('DOCENTE', 'Docente'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    data_nascita = models.DateField(null=True)
    luogo_nascita = models.ForeignKey('comuni_italiani.Comune', on_delete=models.PROTECT, null=True)
    sesso = models.CharField(max_length=1, choices=(('M', 'Maschio'), ('F', 'Femmina')), null=True)
    qualifica = models.CharField(max_length=10, choices=QUALIFICA_CHOICES, null=True)
    datore_lavoro = models.CharField(max_length=100, blank=True, null=True)

    residenza = models.OneToOneField(Indirizzo, on_delete=models.SET_NULL, related_name='residenza', null=True)
    domicilio = models.OneToOneField(Indirizzo, on_delete=models.SET_NULL, related_name='domicilio', null=True)

    @property
    def cf(self):
        if self.data_nascita is None:
            return ''
        date = str(self.data_nascita)
        cf = codicefiscale.encode(surname=self.user.last_name, name=self.user.first_name, sex=self.sesso,
                                  birthdate=date,
                                  birthplace=str(self.luogo_nascita.name))
        return cf

    # Campi per dottorando
    tutor = models.CharField(max_length=100, null=True, blank=True)
    anno_dottorato = models.IntegerField(null=True, blank=True)
    scuola_dottorato = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Profili"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class ModuliMissione(models.Model):
    missione = models.OneToOneField(Missione, on_delete=models.CASCADE)
    parte_1 = models.DateField()
    parte_2 = models.DateField()
    kasko = models.DateField()
    atto_notorio = models.DateField()
    dottorandi = models.DateField()

    parte_1_file = models.FileField(upload_to='moduli/', null=True, blank=True)
    parte_2_file = models.FileField(upload_to='moduli/', null=True, blank=True)
    kasko_file = models.FileField(upload_to='moduli/', null=True, blank=True)
    atto_notorio_file = models.FileField(upload_to='moduli/', null=True, blank=True)
    dottorandi_file = models.FileField(upload_to='moduli/', null=True, blank=True)

    class Meta:
        verbose_name = "Moduli missione"
        verbose_name_plural = "Moduli missioni"
