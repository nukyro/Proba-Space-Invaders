import pygame
import os
import random
import sqlite3
from typing import List, Tuple

pygame.init()

WIDTH, HEIGHT = 1200, 1200
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('pygame')
FONT_PATH = "font/pixel.ttf"
FONT_SIZE = 40
ASSET_PATH = '2proekt'
COOLDOWN = 30
PLAYER_VEL = 5
PLAYER_VEL1 = 10
ENEMY_VEL = 2
LASER_VELO = 5
FPS = 60

font = pygame.font.Font(FONT_PATH, size=FONT_SIZE)
CAT = pygame.transform.scale(pygame.image.load(os.path.join(ASSET_PATH, 'cat.gif')), (100, 100))
ENOT = pygame.transform.scale(pygame.image.load(os.path.join(ASSET_PATH, 'enot.gif')), (100, 100))
FOX = pygame.transform.scale(pygame.image.load(os.path.join(ASSET_PATH, 'fox.gif')), (100, 100))
SHIP_MAIN = pygame.transform.scale(pygame.image.load(os.path.join(ASSET_PATH, 'ship.png')), (125, 125))
BLUE_LASER = pygame.image.load(os.path.join(ASSET_PATH, 'bluelaser.png'))
YELLOW_LASER = pygame.image.load(os.path.join(ASSET_PATH, 'yellowlaser.png'))
BACKGROUND = pygame.transform.scale(pygame.image.load(os.path.join(ASSET_PATH, 'background.png')), (WIDTH, HEIGHT))
EXPLOSION_SOUND = pygame.mixer.Sound(os.path.join(ASSET_PATH, 'explosion.wav'))
LASER_SOUND = pygame.mixer.Sound(os.path.join(ASSET_PATH, 'laser.wav'))
LASER_SOUND.set_volume(0.1)
EXPLOSION_SOUND.set_volume(0.1)

conn = sqlite3.connect('highscore.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS highscore (score INTEGER)''')
conn.commit()


def get_highscore():
    c.execute('SELECT MAX(score) FROM highscore')
    result = c.fetchone()[0]
    return result if result is not None else 0


def save_highscore(score):
    c.execute('INSERT INTO highscore (score) VALUES (?)', (score,))
    conn.commit()


class Laser:
    def __init__(self, x: int, y: int, img: pygame.Surface):
        self.x = x + 13
        self.y = y
        self.img = img
        self.mask = pygame.mask.from_surface(self.img)

    def draw(self, window: pygame.Surface):
        window.blit(self.img, (self.x, self.y))

    def move(self, laser_velo: int):
        self.y += laser_velo

    def off_screen(self, height: int) -> bool:
        return self.y > height or self.y < 0

    def collision(self, obj) -> bool:
        return collide(self, obj)


class Ship:
    def __init__(self, x: int, y: int, health: int = 100):
        self.x = x
        self.y = y
        self.health = health
        self.ship_img = None
        self.laser_img = None
        self.lasers: List[Laser] = []
        self.cool_down_counter = 0

    def draw(self, window: pygame.Surface):
        window.blit(self.ship_img, (self.x, self.y))
        for laser in self.lasers:
            laser.draw(window)

    def move_lasers(self, vel: int, obj):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            elif laser.collision(obj):
                obj.health -= 10
                pygame.mixer.Channel(2).play(EXPLOSION_SOUND)
                self.lasers.remove(laser)

    def cooldown(self):
        if self.cool_down_counter >= COOLDOWN:
            self.cool_down_counter = 0
        elif self.cool_down_counter > 0:
            self.cool_down_counter += 1

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x, self.y, self.laser_img)
            if sound_check(laser):
                pygame.mixer.Channel(0).play(LASER_SOUND)
            self.lasers.append(laser)
            self.cool_down_counter = 1

    def get_width(self) -> int:
        return self.ship_img.get_width()

    def get_height(self) -> int:
        return self.ship_img.get_height()


class Player(Ship):
    def __init__(self, x: int, y: int, health: int = 100):
        super().__init__(x, y, health)
        self.ship_img = SHIP_MAIN
        self.laser_img = YELLOW_LASER
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health

    def move_lasers(self, vel: int, objs: List[Ship], score: int) -> int:
        self.cooldown()
        for laser in self.lasers:
            laser.move(-vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            else:
                for obj in objs:
                    if laser.collision(obj):
                        pygame.mixer.Channel(2).play(EXPLOSION_SOUND)
                        objs.remove(obj)
                        score += 1
                        if laser in self.lasers:
                            self.lasers.remove(laser)
        return score

    def draw(self, window: pygame.Surface):
        super().draw(window)
        self.healthbar(window)

    def healthbar(self, window: pygame.Surface):
        pygame.draw.rect(window, (255, 0, 0), (self.x, self.y + self.get_height() + 10, self.get_width(), 10))
        pygame.draw.rect(window, (0, 255, 0), (
        self.x, self.y + self.get_height() + 10, int(self.get_width() * (self.health / self.max_health)), 10))


class Enemy(Ship):
    COLOR_MAP = {
        'cat1': (CAT, BLUE_LASER),
        'enot1': (ENOT, BLUE_LASER),
        'fox1': (FOX, BLUE_LASER)
    }

    def __init__(self, x: int, y: int, color: str, health: int = 100):
        super().__init__(x, y, health)
        self.ship_img, self.laser_img = self.COLOR_MAP[color]
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health

    def move(self, vel: int):
        self.y += vel

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x - 13, self.y, self.laser_img)
            if sound_check(laser):
                pygame.mixer.Channel(1).play(LASER_SOUND)
            self.lasers.append(laser)
            self.cool_down_counter = 1


def collide(obj1: Laser, obj2: Ship) -> bool:
    offset_x = obj2.x - obj1.x
    offset_y = obj2.y - obj1.y
    return obj1.mask.overlap(obj2.mask, (offset_x, offset_y)) is not None


def sound_check(obj: Laser) -> bool:
    return 0 <= obj.y <= HEIGHT


def main():
    run = True
    lost = False
    lost_count = 0
    level = 0
    lives = 1
    score = 0
    wave_length = 0
    player = Player(550, 1000)
    enemies: List[Enemy] = []

    clock = pygame.time.Clock()
    highscore = get_highscore()

    def redraw_window():
        SCREEN.blit(BACKGROUND, (0, 0))
        level_label = font.render(f'Уровень: {level}', 1, (255, 255, 255))
        lives_label = font.render(f'Жизни: {lives}', 1, (255, 255, 255))
        score_label = font.render(f'Счет: {score}', 1, (255, 255, 255))
        highscore_label = font.render(f'Лучший счет: {highscore}', 1, (255, 255, 255))
        SCREEN.blit(lives_label, (10, 10))
        SCREEN.blit(level_label, (980, 10))
        SCREEN.blit(score_label, (10, 65))
        SCREEN.blit(highscore_label, (10, 120))

        for enemy in enemies:
            enemy.draw(SCREEN)

        player.draw(SCREEN)

        if lost:
            lost_label = font.render(f'Вы проиграли! Ваш счет: {score}', 1, (255, 255, 255))
            SCREEN.blit(lost_label, ((WIDTH - lost_label.get_width()) // 2, (HEIGHT - lost_label.get_height()) // 2))

        pygame.display.update()

    while run:
        clock.tick(FPS)
        redraw_window()

        if lives <= 0 or player.health <= 0:
            lost = True
            lost_count += 1
        if lost:
            if lost_count > FPS * 3:
                if score > highscore:
                    save_highscore(score)
                run = False
            else:
                continue

        if len(enemies) == 0:
            level += 1
            wave_length += 3
            for _ in range(wave_length):
                enemy = Enemy(random.randrange(10, WIDTH - 100), random.randrange(-1500 * (1 + level // 4), -100),
                              random.choice(['cat1', 'enot1', 'fox1']))
                enemies.append(enemy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            player.x -= PLAYER_VEL
        if keys[pygame.K_d]:
            player.x += PLAYER_VEL
        if keys[pygame.K_w]:
            player.y -= PLAYER_VEL
        if keys[pygame.K_s]:
            player.y += PLAYER_VEL
        if keys[pygame.K_1]:
            player.x -= PLAYER_VEL1
        if keys[pygame.K_2]:
            player.x += PLAYER_VEL1

        if pygame.mouse.get_pressed()[0]:
            player.shoot()
        elif keys[pygame.K_SPACE]:
            player.shoot()

        for enemy in enemies[:]:
            enemy.move(ENEMY_VEL)
            enemy.move_lasers(LASER_VELO, player)
            if random.randrange(0, 2 * FPS) == 1:
                enemy.shoot()
            if collide(enemy, player):
                player.health -= 50
                pygame.mixer.Channel(2).play(EXPLOSION_SOUND)
                enemies.remove(enemy)
            elif enemy.y + enemy.get_height() > HEIGHT:
                lives -= 1
                enemies.remove(enemy)

        score = player.move_lasers(LASER_VELO, enemies, score)


def main_menu():
    run = True
    while run:
        title_label = font.render('Нажмите, чтобы продолжить...', 1, (255, 255, 255))
        SCREEN.blit(BACKGROUND, (0, 0))
        SCREEN.blit(title_label, ((WIDTH - title_label.get_width()) // 2, (HEIGHT - title_label.get_height()) // 2))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                main()
    pygame.quit()


if __name__ == "__main__":
    main_menu()
    conn.close()
